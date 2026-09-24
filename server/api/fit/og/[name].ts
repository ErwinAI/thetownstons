import { loadSheetAt, getCharRow } from '../../../utils/fit-store'
import { captureFitOgFromBody, loadDefaultOg, loadStoredOg } from '../../../utils/fit-og'
import { normalizeCharName } from '#shared/fit'

function sendPng(event: Parameters<typeof setHeader>[0], bytes: Buffer, cache: string) {
  setHeader(event, 'Content-Type', 'image/png')
  setHeader(event, 'Cache-Control', cache)
  setHeader(event, 'Content-Length', String(bytes.length))
  if (getMethod(event) === 'HEAD') return null
  return bytes
}

async function fallbackPng(event: Parameters<typeof setHeader>[0], cache: string) {
  const fallback = await loadDefaultOg()
  if (fallback) return sendPng(event, fallback, cache)
  throw createError({ statusCode: 503, statusMessage: 'Could not build preview' })
}

export default defineEventHandler(async (event) => {
  const raw = String(getRouterParam(event, 'name') || '').replace(/\.png$/i, '')
  const name = normalizeCharName(raw)
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Bad character name' })
  }
  try {
    const at = String(getQuery(event).at || '').trim() || undefined
    const row = await getCharRow(name)
    const snap = await loadSheetAt(name, at)
    if (!snap?.body) return fallbackPng(event, 'public, max-age=3600')
    const key = name.toLowerCase()
    const hash = at && snap.id ? `snap-${snap.id}` : (row?.payload_hash || `snap-${snap.id || snap.fetched_at}`)
    const stored = await loadStoredOg(key, hash)
    if (stored?.bytes) return sendPng(event, stored.bytes, 'public, max-age=86400, immutable')
    const made = await captureFitOgFromBody(
      key,
      hash,
      snap.body,
      snap.gold ?? row?.last_gold ?? null,
      snap.played_seconds ?? row?.last_played_seconds ?? null,
    )
    if (made.bytes) return sendPng(event, made.bytes, 'public, max-age=3600')
    return fallbackPng(event, 'public, max-age=300')
  }
  catch (err) {
    console.warn('[fit] og route', err)
    return fallbackPng(event, 'public, max-age=60')
  }
})
