const UPSTREAM = 'https://play.dungeonrunnersreborn.com/api'
const cache = new Map<string, { at: number, body: unknown }>()
const TTL_MS = 20 * 1000

export default defineEventHandler(async (event) => {
  const kind = String(getQuery(event).kind || 'level')
  const allowed = new Set(['level', 'gold', 'played', 'pvp'])
  if (!allowed.has(kind)) {
    throw createError({ statusCode: 400, statusMessage: 'Unknown board' })
  }
  const period = String(getQuery(event).period || '')
  const path = kind === 'pvp' && period ? `/pvp?period=${encodeURIComponent(period)}` : `/${kind}`
  const hit = cache.get(path)
  if (hit && Date.now() - hit.at < TTL_MS) return hit.body

  const res = await fetch(UPSTREAM + path, { headers: { Accept: 'application/json' } })
  if (!res.ok) {
    throw createError({ statusCode: res.status, statusMessage: `Board HTTP ${res.status}` })
  }
  const body = await res.json()
  cache.set(path, { at: Date.now(), body })
  setHeader(event, 'Cache-Control', 'public, max-age=15')
  return body
})
