import { isFitHost, isFitPassthrough, WIKI_ORIGIN } from '#shared/fit'

export default defineEventHandler((event) => {
  const host = getRequestHeader(event, 'host') || ''
  if (!isFitHost(host)) return

  const url = getRequestURL(event)
  const path = url.pathname || '/'

  if (path === '/wiki' || path.startsWith('/wiki/')) {
    return sendRedirect(event, `${WIKI_ORIGIN}${path}${url.search}`, 302)
  }

  if (isFitPassthrough(path) || path.startsWith('/fit')) return

  const next = (path === '/' ? '/fit/' : `/fit${path}`) + url.search
  event.node.req.url = next
})
