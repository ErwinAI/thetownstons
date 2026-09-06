import { listRecentChanges } from '../utils/wiki-db'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  return listRecentChanges({
    user: query.user ? String(query.user) : undefined,
    limit: query.limit ? Number(query.limit) : undefined,
  })
})
