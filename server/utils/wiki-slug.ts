import { mergeQuestionTitle } from '#shared/wiki'

export function wikiSlugFromEvent(event: Parameters<typeof getRouterParam>[0], prefix: string): string {
  const slug = (getRouterParam(event, 'slug') || '').replace(/\/+$/, '')
  const full = (event.node?.req?.url || event.path || '').replace(prefix, '')
  const q = full.indexOf('?')
  const pathOnly = (q >= 0 ? full.slice(0, q) : full).replace(/\/+$/, '')
  const search = q >= 0 ? full.slice(q) : ''
  const raw = mergeQuestionTitle(pathOnly, search)
  try {
    return decodeURIComponent(raw)
  }
  catch {
    return raw || slug
  }
}
