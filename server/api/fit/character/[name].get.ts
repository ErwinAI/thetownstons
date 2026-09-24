import { getCharacterView } from '../../../utils/fit-store'
import { normalizeCharName } from '#shared/fit'

export default defineEventHandler(async (event) => {
  const name = normalizeCharName(getRouterParam(event, 'name') || '')
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Bad character name' })
  }
  const at = String(getQuery(event).at || '').trim() || undefined
  const payload = await getCharacterView(name, at)
  setHeader(event, 'Cache-Control', at ? 'public, max-age=120' : 'public, max-age=30')
  return payload
})
