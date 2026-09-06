import { assertAdmin } from '../../utils/access'
import { userFromRequest, serviceClient } from '../../utils/supabase'

export default defineEventHandler(async (event) => {
  const user = await userFromRequest(event)
  if (!user) throw createError({ statusCode: 401, statusMessage: 'Log in' })
  await assertAdmin(user.id)

  const id = getRouterParam(event, 'id') || ''
  const body = await readBody<{ action?: string }>(event)
  const action = body?.action
  if (action !== 'approve' && action !== 'reject') {
    throw createError({ statusCode: 400, statusMessage: 'approve or reject' })
  }

  const db = serviceClient()
  if (!db) throw createError({ statusCode: 503, statusMessage: 'Wiki store is not configured' })

  const status = action === 'approve' ? 'approved' : 'rejected'
  const { error } = await db.from('wiki_images').update({
    status,
    reviewed_at: new Date().toISOString(),
    reviewed_by: user.id,
  }).eq('id', id)
  if (error) throw createError({ statusCode: 500, statusMessage: error.message })
  return { id, status }
})
