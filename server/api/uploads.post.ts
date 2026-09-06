import { assertCanEdit, assertEmailConfirmed } from '../utils/access'
import { userFromRequest, serviceClient } from '../utils/supabase'

const ALLOWED = new Set(['image/jpeg', 'image/png', 'image/gif', 'image/webp'])
const MAX = 2 * 1024 * 1024

export default defineEventHandler(async (event) => {
  const user = await userFromRequest(event)
  if (!user) throw createError({ statusCode: 401, statusMessage: 'Log in to upload' })
  assertEmailConfirmed(user)
  await assertCanEdit(user.id)

  const form = await readMultipartFormData(event)
  const file = form?.find((part) => part.name === 'file' && part.data)
  if (!file?.data?.length || !file.filename) {
    throw createError({ statusCode: 400, statusMessage: 'Choose an image' })
  }
  const mime = file.type || 'application/octet-stream'
  if (!ALLOWED.has(mime)) {
    throw createError({ statusCode: 400, statusMessage: 'Use jpeg, png, gif, or webp' })
  }
  if (file.data.length > MAX) {
    throw createError({ statusCode: 400, statusMessage: 'Image must be under 2 MB' })
  }

  const db = serviceClient()
  if (!db) throw createError({ statusCode: 503, statusMessage: 'Wiki store is not configured' })

  const ext = mime === 'image/png' ? 'png' : mime === 'image/gif' ? 'gif' : mime === 'image/webp' ? 'webp' : 'jpg'
  const id = crypto.randomUUID()
  const storagePath = `pending/${user.id}/${id}.${ext}`
  const { error: upErr } = await db.storage.from('wiki').upload(storagePath, file.data, {
    contentType: mime,
    upsert: false,
  })
  if (upErr) {
    throw createError({ statusCode: 500, statusMessage: upErr.message })
  }

  const { data, error } = await db.from('wiki_images').insert({
    id,
    storage_path: storagePath,
    mime,
    original_name: file.filename,
    status: 'pending',
    uploaded_by: user.id,
  }).select('id, status').single()
  if (error || !data) {
    throw createError({ statusCode: 500, statusMessage: error?.message || 'Upload failed' })
  }

  return { id: data.id, status: data.status, src: `/api/uploads/${data.id}` }
})
