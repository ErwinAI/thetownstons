import { findWikiPage } from '../utils/wiki'
import { wikiApiPath } from '#shared/wiki'

export default defineEventHandler((event) => {
  const raw = (event.node?.req?.url || event.path || '').split('?')[0]
  const isApi = raw.startsWith('/api/wiki/')
  if (!isApi && !raw.startsWith('/wiki/')) return

  let slug = raw.replace(/^\/api\/wiki\//, '').replace(/^\/wiki\//, '').replace(/\/+$/, '')
  if (!slug || slug.includes('.')) return
  try {
    slug = decodeURIComponent(slug)
  }
  catch {
    // keep raw
  }

  const page = findWikiPage(slug)
  if (!page) return

  const canonical = isApi ? wikiApiPath(page.path) : page.path
  const requested = raw.replace(/\/+$/, '')
  if (requested === canonical) return

  return sendRedirect(event, canonical, 301)
})
