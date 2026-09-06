import { revertWikiPage } from '../../utils/wiki-db'
import { assertAdmin } from '../../utils/access'
import { userFromRequest } from '../../utils/supabase'
import { wikiSlugFromEvent } from '../../utils/wiki-slug'

export default defineEventHandler(async (event) => {
  const user = await userFromRequest(event)
  if (!user) {
    throw createError({ statusCode: 401, statusMessage: 'Log in to revert' })
  }
  await assertAdmin(user.id)
  const decoded = wikiSlugFromEvent(event, /^\/api\/history\//)
  const body = await readBody<{ id?: number }>(event)
  const id = Number(body?.id || 0)
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'Revision id is required' })
  }
  return revertWikiPage(decoded, id, user.email || user.id, user.id)
})
