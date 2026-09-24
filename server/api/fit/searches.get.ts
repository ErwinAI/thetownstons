import { listFitSearches } from '../../utils/fit-store'

export default defineEventHandler(async (event) => {
  setHeader(event, 'Cache-Control', 'public, max-age=15')
  return await listFitSearches()
})
