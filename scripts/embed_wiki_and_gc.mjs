import { createClient } from '@supabase/supabase-js'
import { createGateway, embedMany } from 'ai'
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

const DUMP_DIR = process.env.DUMP_DIR
  || 'C:\\Users\\me\\Dungeon_Runners_Client_666\\dravex_v1.0.0.0_by_atom0s'
const SKIP_DIRS = new Set(['effects', 'misc', 'world', 'ncs', 'sound', 'sounds', 'music'])
const SKIP_SLUG = /^(Talk\/|User\/|Special\/|Template\/)/i
const EMBED_BATCH = 64
const UPSERT_BATCH = 80

const KIND = {
  '1H Sword': 'one-handed sword',
  '2H Sword': 'two-handed sword',
  '1H Axe': 'one-handed axe',
  '2H Axe': 'two-handed axe',
  '1H Mace': 'one-handed mace',
  '2H Mace': 'two-handed mace',
  '1H Pick': 'one-handed pick',
  '2H Pick': 'two-handed pick',
  '1H Staff': 'one-handed staff',
  '2H Staff': 'two-handed staff',
  '1H Gun': 'one-handed gun',
  '2H Gun': 'two-handed gun',
  '2H Crossbow': 'two-handed crossbow',
  '2H Cannon': 'two-handed cannon',
  Plate: 'plate',
  Scale: 'scale',
  Crystal: 'crystal',
  Leather: 'leather',
  Chain: 'chain',
  Splint: 'splint',
  Ring: 'ring',
  Amulet: 'amulet',
}

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

function stripHtml(value) {
  return String(value || '')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
    .replace(/\s+/g, ' ')
    .trim()
}

function chunkText(text, size = 900, overlap = 80) {
  if (text.length <= size) return text.length >= 40 ? [text] : []
  const out = []
  let i = 0
  while (i < text.length) {
    let end = Math.min(text.length, i + size)
    if (end < text.length) {
      const cut = text.lastIndexOf(' ', end)
      if (cut > i + 400) end = cut
    }
    const piece = text.slice(i, end).trim()
    if (piece.length >= 40) out.push(piece)
    if (end >= text.length) break
    i = Math.max(end - overlap, i + 1)
  }
  return out
}

function compact(text) {
  return String(text || '').toLowerCase().replace(/[^a-z0-9]+/g, '')
}

function unquote(raw) {
  const value = String(raw || '').trim()
  if (value.startsWith('"') && value.endsWith('"')) {
    return value.slice(1, -1).replace(/\\"/g, '"')
  }
  return value
}

function walkGc(dir, files) {
  if (!existsSync(dir)) return
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    let stat
    try {
      stat = statSync(full)
    }
    catch {
      continue
    }
    if (stat.isDirectory()) {
      if (SKIP_DIRS.has(name.toLowerCase())) continue
      walkGc(full, files)
      continue
    }
    if (name.toLowerCase().endsWith('.gc')) files.push(full)
  }
}

function parseGameFacts(dumpDir) {
  const files = []
  walkGc(dumpDir, files)
  const byLabel = new Map()
  const assign = /\b(Label|Summary|Journal|Offer|TurnIn|QuestDescription|QuestReward|InventoryIcon|WeaponSpeed|Damage|SoulBound|Quality|ItemType|Type)\s*=\s*("(?:[^"\\]|\\.)*"|[A-Za-z0-9_.\-'][\w.\-']*)\s*;/g

  for (const file of files) {
    let text
    try {
      text = readFileSync(file, 'utf8')
    }
    catch {
      continue
    }
    if (!text.includes('Label')) continue
    text = text.replace(/(?<!\/)\/\*[\s\S]*?\*\//g, '')
    let current = null
    for (const match of text.matchAll(assign)) {
      const kind = match[1]
      const val = unquote(match[2])
      if (kind === 'Label' && val && !['NONE', 'PREFIX', 'SUFFIX'].includes(val)) {
        if (current?.label) {
          const key = compact(current.label)
          if (key && (!byLabel.has(key) || (current.lines.length > (byLabel.get(key).lines.length || 0)))) {
            byLabel.set(key, current)
          }
        }
        current = { label: val, lines: [] }
        continue
      }
      if (!current) continue
      if (kind === 'InventoryIcon') continue
      if (kind === 'SoulBound' && val.toLowerCase() === 'true') current.lines.push('This item is soulbound.')
      else if (kind === 'Damage') current.lines.push(`Damage ${val}.`)
      else if (kind === 'WeaponSpeed') current.lines.push(`Attack speed ${val}.`)
      else if (kind === 'Quality') current.quality = val
      else if ((kind === 'ItemType' || kind === 'Type') && KIND[val]) current.kind = KIND[val]
      else if (['Summary', 'Journal', 'Offer', 'TurnIn', 'QuestDescription', 'QuestReward'].includes(kind) && val.length > 8) {
        current.lines.push(val)
      }
    }
    if (current?.label) {
      const key = compact(current.label)
      if (key && (!byLabel.has(key) || (current.lines.length > (byLabel.get(key).lines.length || 0)))) {
        byLabel.set(key, current)
      }
    }
  }

  const chunks = []
  for (const row of byLabel.values()) {
    const bits = []
    if (row.kind) bits.push(`${row.label} is a ${row.kind}.`)
    else bits.push(row.label)
    if (row.quality && /mythic/i.test(row.quality)) bits.push('Rainbow item.')
    bits.push(...row.lines)
    const text = bits.join(' ').replace(/\s+/g, ' ').trim()
    if (text.length < 24) continue
    chunks.push({
      source: 'game',
      ref: compact(row.label).slice(0, 80),
      path: '',
      title: row.label,
      chunk_i: 0,
      text: text.slice(0, 1600),
    })
  }
  return chunks
}

async function loadWikiPages(db) {
  const pages = []
  let from = 0
  while (true) {
    const { data, error } = await db
      .from('pages')
      .select('slug, title, path, html, body_md, description')
      .range(from, from + 499)
    if (error) throw new Error(error.message)
    if (!data?.length) break
    pages.push(...data)
    if (data.length < 500) break
    from += 500
  }
  return pages
}

function wikiChunks(pages) {
  const out = []
  for (const page of pages) {
    const slug = String(page.slug || '')
    if (SKIP_SLUG.test(slug)) continue
    const title = String(page.title || '').trim()
    if (!title) continue
    const body = stripHtml(page.body_md || page.html || '')
    const lead = [title, page.description, body].filter(Boolean).join('. ')
    const pieces = chunkText(lead)
    pieces.forEach((text, chunk_i) => {
      out.push({
        source: 'wiki',
        ref: slug.slice(0, 180),
        path: String(page.path || `/wiki/${slug}`),
        title,
        chunk_i,
        text,
      })
    })
  }
  return out
}

async function embedAndStore(db, gateway, chunks, source) {
  await db.from('wiki_chunks').delete().eq('source', source)
  for (let i = 0; i < chunks.length; i += EMBED_BATCH) {
    const batch = chunks.slice(i, i + EMBED_BATCH)
    const { embeddings } = await embedMany({
      model: gateway.embeddingModel('openai/text-embedding-3-small'),
      values: batch.map((row) => `${row.title}\n${row.text}`.slice(0, 8000)),
    })
    const rows = batch.map((row, idx) => ({
      ...row,
      embedding: embeddings[idx],
    }))
    for (let j = 0; j < rows.length; j += UPSERT_BATCH) {
      const slice = rows.slice(j, j + UPSERT_BATCH)
      const { error } = await db.from('wiki_chunks').insert(slice)
      if (error) throw new Error(error.message)
    }
    console.log(`  ${source} ${Math.min(i + batch.length, chunks.length)}/${chunks.length}`)
  }
}

loadEnv()

const wikiOnly = process.argv.includes('--wiki-only')
const gameOnly = process.argv.includes('--game-only')
const url = process.env.NUXT_PUBLIC_SUPABASE_URL
const key = process.env.NUXT_SUPABASE_SERVICE_ROLE_KEY
const apiKey = process.env.NUXT_AI_GATEWAY_API_KEY || process.env.AI_GATEWAY_API_KEY
if (!url || !key) {
  console.error('Missing NUXT_PUBLIC_SUPABASE_URL or NUXT_SUPABASE_SERVICE_ROLE_KEY')
  process.exit(1)
}
if (!apiKey) {
  console.error('Missing NUXT_AI_GATEWAY_API_KEY')
  process.exit(1)
}

const db = createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } })
const gateway = createGateway({ apiKey })

if (!gameOnly) {
  console.log('Loading wiki pages…')
  const pages = await loadWikiPages(db)
  const chunks = wikiChunks(pages)
  console.log(`Embedding ${chunks.length} wiki chunks from ${pages.length} pages`)
  await embedAndStore(db, gateway, chunks, 'wiki')
}

if (!wikiOnly) {
  if (!existsSync(DUMP_DIR)) {
    console.log(`No game dump at ${DUMP_DIR} — skip game facts`)
  }
  else {
    console.log('Reading game facts…')
    const chunks = parseGameFacts(DUMP_DIR)
    console.log(`Embedding ${chunks.length} game facts`)
    await embedAndStore(db, gateway, chunks, 'game')
  }
}

console.log('Done.')
