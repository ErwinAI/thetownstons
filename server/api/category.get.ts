import { categoryLists } from '../utils/wiki-db'

export default defineEventHandler(async (event) => {
  const name = String(getQuery(event).name || '').trim()
  if (!name) return { members: [], subcats: [] }
  return categoryLists(name)
})
