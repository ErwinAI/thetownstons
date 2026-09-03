export default defineEventHandler((event) => {
  const slug = (getRouterParam(event, 'slug') || '').replace(/\/+$/, '')
  const raw = (event.node?.req?.url || event.path || '')
    .split('?')[0]
    .replace(/^\/api\/wiki\//, '')
    .replace(/\/+$/, '')
  let decoded = raw
  try {
    decoded = decodeURIComponent(raw)
  }
  catch {
    // keep raw
  }
  const page = findWikiPage(slug) || findWikiPage(decoded) || findWikiPage(raw)
  if (!page) {
    throw createError({ statusCode: 404, statusMessage: 'Page not found' })
  }
  return page
})
