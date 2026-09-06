import { findWikiPage } from '../utils/wiki'
import { isSameWikiPath, mergeQuestionTitle, wikiApiPath, wikiHref } from '#shared/wiki'

export default defineEventHandler((event) => {
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
  const page = findWikiPage(slug)
  if (!page) return

  // Same title, different encoding ("," vs "%2C") — do not 301. Hosts decode
  // percent-escapes and that loop is the perpetual spinner.
  if (isSameWikiPath(slug, page.path)) return

  const dest = isApi ? wikiApiPath(page.path) : wikiHref(page.path)
  return sendRedirect(event, dest, 301)
})
