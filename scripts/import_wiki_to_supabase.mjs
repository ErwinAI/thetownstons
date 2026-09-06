import { createClient } from '@supabase/supabase-js'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

function loadEnv() {
  const text = readFileSync(join(process.cwd(), '.env'), 'utf8')
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq === -1) continue
    const key = trimmed.slice(0, eq).trim()
    let value = trimmed.slice(eq + 1).trim()
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1)
    }
    if (process.env[key] === undefined) process.env[key] = value
  }
}

function normalizeWikiPath(value) {
  let text = value.replace(/^\/wiki\//, '').replace(/_/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase()
  try {
    text = decodeURIComponent(text)
  }
  catch {
    // keep
  }
  if (text.startsWith('category/')) text = `category:${text.slice('category/'.length)}`
  return text
}

const SLUG_ALIASES = {
  shrines: 'attribute shrine',
  shrine: 'attribute shrine',
  "abaddon's handy candy boomstick": "abaddon's handy candy broomstick",
  "nai's flak jacket": "naj's flak jacket",
  "najas flak jacket": "naj's flak jacket",
  "doc wyvern's boots": "doc wyvern's",
  "sissirat's brother's cousin's roommate's staff of something really awesome":
    "sissirat's brother's cousin's roomate's staff of something really awesome",
  azzaz: 'azza zin',
  'azza zins': 'azza zin',
  azzazin: 'azza zin',
  'love/hate (mostly hate)': 'love hate (mostly hate)',
  'love hate mostly hate': 'love hate (mostly hate)',
  "king's coin": "king's coins",
  'kings coin': "king's coins",
  'kings coins': "king's coins",
  amazonian: 'draykop the amazon',
  'the amazonian': 'draykop the amazon',
}

function walk(dir, acc) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) {
      walk(full, acc)
      continue
    }
    if (!name.endsWith('.json')) continue
    const page = JSON.parse(readFileSync(full, 'utf8'))
    if (page?.path && page.title) acc.push(page)
  }
}

loadEnv()

const url = process.env.NUXT_PUBLIC_SUPABASE_URL
const key = process.env.NUXT_SUPABASE_SERVICE_ROLE_KEY || process.env.NUXT_PUBLIC_SUPABASE_ANON_KEY
if (!url || !key) {
  console.error('Missing NUXT_PUBLIC_SUPABASE_URL or a secret/anon key in .env')
  process.exit(1)
}

const supabase = createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } })
const pages = []
walk(join(process.cwd(), 'content/wiki'), pages)

const rawRows = pages.map((page) => {
  const slug = String(page.path).replace(/^\/wiki\//, '')
  return {
    slug,
    fold_key: normalizeWikiPath(slug),
    title: page.title,
    wiki_title: page.wikiTitle || slug,
    path: page.path,
    description: page.description || null,
    html: page.html || '',
    body_md: null,
    categories: page.categories || [],
    images: page.images || [],
  }
})

function richer(a, b) {
  return (a.html || '').length >= (b.html || '').length ? a : b
}

const bySlug = new Map()
for (const row of rawRows) {
  const prev = bySlug.get(row.slug)
  bySlug.set(row.slug, prev ? richer(row, prev) : row)
}

const extraAliases = []
const byFold = new Map()
for (const row of bySlug.values()) {
  const prev = byFold.get(row.fold_key)
  if (!prev) {
    byFold.set(row.fold_key, row)
    continue
  }
  const keep = richer(row, prev)
  const drop = keep === row ? prev : row
  byFold.set(row.fold_key, keep)
  if (drop.slug !== keep.slug && drop.fold_key !== keep.fold_key) {
    extraAliases.push({ alias: drop.fold_key, slug: keep.slug })
  }
}

const rows = [...byFold.values()]
if (bySlug.size !== rawRows.length) {
  console.log(`Deduped slugs: ${rawRows.length} files -> ${bySlug.size} paths`)
}
if (rows.length !== bySlug.size) {
  console.log(`Deduped fold keys: ${bySlug.size} paths -> ${rows.length} pages`)
}

const chunk = 80
for (let i = 0; i < rows.length; i += chunk) {
  const slice = rows.slice(i, i + chunk)
  const { error } = await supabase.from('pages').upsert(slice, { onConflict: 'slug' })
  if (error) {
    console.error(`Upsert failed at ${i}: ${error.message}`)
    process.exit(1)
  }
  console.log(`Imported ${Math.min(i + chunk, rows.length)} / ${rows.length}`)
}

const foldToSlug = new Map(rows.map((row) => [row.fold_key, row.slug]))
const aliases = [
  ...extraAliases,
  ...Object.entries(SLUG_ALIASES)
    .map(([alias, target]) => {
      const slug = foldToSlug.get(target)
      return slug ? { alias, slug } : null
    })
    .filter(Boolean),
]
const aliasByKey = new Map()
for (const item of aliases) {
  if (item.alias && item.alias !== normalizeWikiPath(item.slug)) aliasByKey.set(item.alias, item)
}
const uniqueAliases = [...aliasByKey.values()]

if (uniqueAliases.length) {
  const { error } = await supabase.from('page_aliases').upsert(uniqueAliases, { onConflict: 'alias' })
  if (error) {
    console.error(`Alias import failed: ${error.message}`)
    process.exit(1)
  }
}

console.log(`Done. ${rows.length} pages, ${uniqueAliases.length} aliases.`)
