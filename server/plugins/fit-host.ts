import { isFitHost, isFitPassthrough } from '#shared/fit'

export default defineNitroPlugin((nitro) => {
  nitro.hooks.hook('request', (event) => {
    const host = getRequestHeader(event, 'host') || ''
    if (!isFitHost(host)) return
    const url = getRequestURL(event)
    const path = url.pathname || '/'
    if (isFitPassthrough(path) || path.startsWith('/fit') || path.startsWith('/wiki')) return
    const next = (path === '/' ? '/fit/' : `/fit${path}`) + url.search
    event.node.req.url = next
  })
})
