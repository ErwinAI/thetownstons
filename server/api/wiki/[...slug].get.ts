export default defineEventHandler((event) => {
  const slug = (getRouterParam(event, 'slug') || '').replace(/\/+$/, '')
  const page = findWikiPage(slug)
  if (!page) {
    throw createError({ statusCode: 404, statusMessage: 'Page not found' })
  }
  return page
})
