import { assertAdmin } from '../utils/access'
import { userFromRequest, serviceClient } from '../utils/supabase'

export default defineEventHandler(async (event) => {
  const user = await userFromRequest(event)
  if (!user) throw createError({ statusCode: 401, statusMessage: 'Log in' })
  await assertAdmin(user.id)

  const status = String(getQuery(event).status || 'pending')
  const db = serviceClient()
  if (!db) return []
  const { data } = await db
    .from('wiki_images')
    .select('id, original_name, status, created_at, uploaded_by')
    .eq('status', status)
    .order('created_at', { ascending: false })
    .limit(200)

  const ids = [...new Set((data || []).map((row) => row.uploaded_by).filter(Boolean))]
  const names = new Map<string, string>()
  if (ids.length) {
    const { data: users } = await db.from('users').select('id, username').in('id', ids)
    for (const row of users || []) names.set(row.id, row.username)
  }

  return (data || []).map((row) => ({
    id: row.id,
    original_name: row.original_name,
    status: row.status,
    created_at: row.created_at,
    username: names.get(row.uploaded_by) || 'user',
    src: `/api/uploads/${row.id}`,
  }))
})
