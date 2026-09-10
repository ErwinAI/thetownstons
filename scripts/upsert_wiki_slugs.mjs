import { createClient } from '@supabase/supabase-js'
import { readFileSync } from 'node:fs'
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

loadEnv()

const url = process.env.NUXT_PUBLIC_SUPABASE_URL
const key = process.env.NUXT_SUPABASE_SERVICE_ROLE_KEY || process.env.NUXT_PUBLIC_SUPABASE_ANON_KEY
if (!url || !key) {
  console.error('Missing NUXT_PUBLIC_SUPABASE_URL or a secret/anon key in .env')
  process.exit(1)
}

const files = process.argv.slice(2)
if (!files.length) {
  console.error('Usage: node scripts/upsert_wiki_slugs.mjs content/wiki/Foo.json ...')
  process.exit(1)
}

const supabase = createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } })
const rows = []
const aliases = []

for (const file of files) {
  const page = JSON.parse(readFileSync(file, 'utf8'))
  const slug = String(page.path).replace(/^\/wiki\//, '')
  const fold = normalizeWikiPath(slug)
  rows.push({
    slug,
    fold_key: fold,
    title: page.title,
    wiki_title: page.wikiTitle || slug,
    path: page.path,
    description: page.description || null,
    html: page.html || '',
    body_md: null,
    categories: page.categories || [],
    images: page.images || [],
  })
  if (fold !== slug.toLowerCase()) {
    aliases.push({ alias: fold, slug })
  }
}

const { error } = await supabase.from('pages').upsert(rows, { onConflict: 'slug' })
if (error) {
  console.error(error.message)
  process.exit(1)
}
if (aliases.length) {
  const { error: aliasError } = await supabase.from('page_aliases').upsert(aliases, { onConflict: 'alias' })
  if (aliasError) {
    console.error(aliasError.message)
    process.exit(1)
  }
}
console.log(`Upserted ${rows.length} pages`)
