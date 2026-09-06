import { createGateway, embed } from 'ai'
import { capHits, KARL_LIMITS, type KarlHit } from './karl'
import { serviceClient } from './supabase'
import { resolveWikiPage, searchWiki } from './wiki-db'

type ChunkRow = {
  title: string
  path: string
  text: string
  distance: number
}

function gatewayFromConfig() {
  const apiKey = String(
    useRuntimeConfig().aiGatewayApiKey
    || process.env.AI_GATEWAY_API_KEY
    || process.env.NUXT_AI_GATEWAY_API_KEY
    || '',
  )
  if (!apiKey) return null
  return createGateway({ apiKey })
}

export async function embedQuery(query: string): Promise<number[]> {
  const gateway = gatewayFromConfig()
  if (!gateway) {
    throw createError({ statusCode: 503, statusMessage: 'KarlAI is not configured' })
  }
  const { embedding } = await embed({
    model: gateway.embeddingModel('openai/text-embedding-3-small'),
    value: query,
  })
  return embedding
}

function withTimeout<T>(work: Promise<T>, ms: number): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Karl search timed out')), ms)
    work.then((value) => {
      clearTimeout(timer)
      resolve(value)
    }, (err) => {
      clearTimeout(timer)
      reject(err)
    })
  })
}

export async function matchChunks(query: string, source: 'wiki' | 'game', limit?: number): Promise<KarlHit[]> {
  const db = serviceClient()
  if (!db) return []
  const take = limit ?? (source === 'wiki' ? KARL_LIMITS.wikiHits : KARL_LIMITS.gameHits)
  const budget = source === 'wiki' ? KARL_LIMITS.wikiChars : KARL_LIMITS.gameChars
  const embedding = await withTimeout(embedQuery(query), 12000)
  const { data, error } = await withTimeout(db.rpc('match_chunks', {
    query_embedding: embedding,
    match_count: take,
    source_filter: source,
  }), 8000)
  if (error || !Array.isArray(data)) return []
  const hits = (data as ChunkRow[])
    .filter((row) => row.text && row.title)
    .map((row) => ({
      title: String(row.title),
      path: source === 'wiki' ? String(row.path || '') : '',
      text: String(row.text),
    }))
  return capHits(hits, budget)
}

function expandWikiQuery(query: string): string[] {
  const q = query.toLowerCase()
  const extra: string[] = []
  if (/\b(dual|two[- ]stat|agi(?:lity)?|intellect|endurance|prefix|postfix|descriptor|modifier)\b/.test(q)) {
    extra.push('Name Descriptors')
    extra.push('Modifiers')
  }
  if (/\b(best|bis|best in slot)\b/.test(q)) {
    extra.push(query.replace(/\b(best in slot|best|bis)\b/gi, '').trim() || query)
    if (/\bring/.test(q)) extra.push('Rainbow Rings')
    if (/\bamulet/.test(q)) extra.push('Rainbow Amulets')
  }
  return [...new Set([query, ...extra].filter((row) => row.length >= 2))].slice(0, 3)
}

function stripPlain(value: string): string {
  return String(value || '')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

export async function retrieveWiki(query: string): Promise<KarlHit[]> {
  const queries = expandWikiQuery(query)
  const semantic = (await Promise.all(queries.map((q) => matchChunks(q, 'wiki')))).flat()
  const lexical = await searchWiki(query).catch(() => [])
  const byPath = new Map<string, KarlHit>()
  for (const hit of semantic) {
    const key = (hit.path || hit.title).toLowerCase()
    if (!byPath.has(key)) byPath.set(key, hit)
  }
  const titled = lexical.slice(0, 6)
  for (const row of titled) {
    const key = String(row.path || '').toLowerCase()
    if (!key || byPath.has(key)) continue
    const page = await resolveWikiPage(row.path.replace(/^\/wiki\//, ''))
    const text = stripPlain(page?.body_md || page?.html || row.headline || '')
    if (!text) continue
    byPath.set(key, {
      title: page?.title || row.title,
      path: page?.path || row.path,
      text: text.slice(0, 1600),
    })
  }
  return capHits([...byPath.values()], KARL_LIMITS.wikiChars, KARL_LIMITS.chunkChars)
}
