import { searchWiki } from '../utils/wiki-db'

export default defineEventHandler((event) => {
  const q = String(getQuery(event).q || '')
  return searchWiki(q)
})
