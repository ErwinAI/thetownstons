import { diffWikiRevision, getWikiRevision, listWikiRevisions } from '../../utils/wiki-db'
import { wikiSlugFromEvent } from '../../utils/wiki-slug'

export default defineEventHandler(async (event) => {
  const decoded = wikiSlugFromEvent(event, /^\/api\/history\//)
  const query = getQuery(event)
  const id = Number(query.id || 0)
  if (id && String(query.diff || '') === '1') {
    return diffWikiRevision(decoded, id)
  }
  if (id) {
    const revision = await getWikiRevision(decoded, id)
    if (!revision) throw createError({ statusCode: 404, statusMessage: 'Revision not found' })
    return { revision }
  }
  const { page, revisions } = await listWikiRevisions(decoded)
  if (!page && !revisions.length) {
    throw createError({ statusCode: 404, statusMessage: 'Page not found' })
  }
  return { page, revisions }
})
