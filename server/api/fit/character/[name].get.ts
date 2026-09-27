import { getCharacterView, recordFitSearch } from '../../../utils/fit-store'
import { normalizeCharName } from '#shared/fit'

export default defineEventHandler(async (event) => {
  const name = normalizeCharName(getRouterParam(event, 'name') || '')
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Bad character name' })
  }
  const query = getQuery(event)
  const at = String(query.at || '').trim() || undefined
  const liveFlag = Array.isArray(query.live) ? query.live[0] : query.live
  const live = !at && (liveFlag === '1' || liveFlag === 'true')
  const payload = await getCharacterView(name, at, live)
  if (!at) await recordFitSearch(payload.name)
  setHeader(event, 'Cache-Control', at ? 'public, max-age=120' : live ? 'public, max-age=15' : 'public, max-age=30')
  return payload
})
