import { loadHistory } from '../../../../utils/fit-store'
import { normalizeCharName } from '#shared/fit'

export default defineEventHandler(async (event) => {
  const name = normalizeCharName(getRouterParam(event, 'name') || '')
  if (!name) {
    throw createError({ statusCode: 400, statusMessage: 'Bad character name' })
  }
  const data = await loadHistory(name)
  setHeader(event, 'Cache-Control', 'public, max-age=30')
  return data
})
