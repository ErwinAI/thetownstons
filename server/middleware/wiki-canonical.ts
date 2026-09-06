import { isSameWikiPath, mergeQuestionTitle, wikiApiPath, wikiHref } from '#shared/wiki'
import { resolveWikiPage } from '../utils/wiki-db'

export default defineEventHandler(async (event) => {
  const full = (event.node?.req?.url || event.path || '')
  const q = full.indexOf('?')
  const pathOnly = (q >= 0 ? full.slice(0, q) : full).split('#')[0]
  const search = q >= 0 ? full.slice(q) : ''
  const raw = mergeQuestionTitle(pathOnly, search)
  const isApi = raw.startsWith('/api/wiki/')
  if (!isApi && !raw.startsWith('/wiki/')) return

  let slug = raw.replace(/^\/api\/wiki\//, '').replace(/^\/wiki\//, '').replace(/\/+$/, '')
  if (!slug || /\.[a-z0-9]{2,5}$/i.test(slug)) return
  try {
    slug = decodeURIComponent(slug)
  }
  catch {
    // keep raw
  }
  const page = await resolveWikiPage(slug)
  if (!page) return

  if (isSameWikiPath(slug, page.path)) return

  const dest = isApi ? wikiApiPath(page.path) : wikiHref(page.path)
  return sendRedirect(event, dest, 301)
})
