import { assertAdmin, setOpenEdits } from '../utils/access'
import { userFromRequest } from '../utils/supabase'

export default defineEventHandler(async (event) => {
  const user = await userFromRequest(event)
  if (!user) throw createError({ statusCode: 401, statusMessage: 'Log in' })
  await assertAdmin(user.id)
  const body = await readBody<{ open_edits?: boolean }>(event)
  if (typeof body?.open_edits !== 'boolean') {
    throw createError({ statusCode: 400, statusMessage: 'open_edits required' })
  }
  await setOpenEdits(body.open_edits)
  return { open_edits: body.open_edits }
})
