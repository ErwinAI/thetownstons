import { openEditsEnabled } from '../utils/access'

export default defineEventHandler(async () => {
  return { open_edits: await openEditsEnabled() }
})
