import { createGateway, embed } from 'ai'
import { capHits, KARL_LIMITS, type KarlHit } from './karl'
import { serviceClient } from './supabase'

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
