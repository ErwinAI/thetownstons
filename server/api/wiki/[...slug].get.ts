import { mergeQuestionTitle } from '#shared/wiki'
import { resolveWikiPage } from '../../utils/wiki-db'

export default defineEventHandler(async (event) => {
  const slug = (getRouterParam(event, 'slug') || '').replace(/\/+$/, '')
  const full = (event.node?.req?.url || event.path || '').replace(/^\/api\/wiki\//, '')
  const q = full.indexOf('?')
  const pathOnly = (q >= 0 ? full.slice(0, q) : full).replace(/\/+$/, '')
  const search = q >= 0 ? full.slice(q) : ''
  const raw = mergeQuestionTitle(pathOnly, search)
  let decoded = raw
  try {
    decoded = decodeURIComponent(raw)
  }
  catch {
    // keep raw
  }
  const page = await resolveWikiPage(slug) || await resolveWikiPage(decoded) || await resolveWikiPage(raw)
  if (!page) {
    throw createError({ statusCode: 404, statusMessage: 'Page not found' })
  }
  return page
})
