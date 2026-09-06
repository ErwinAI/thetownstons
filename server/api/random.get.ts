import { randomWikiPath } from '../utils/wiki-db'

export default defineEventHandler(async () => {
  const path = await randomWikiPath()
  return { path: path || '/all' }
})
