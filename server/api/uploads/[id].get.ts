import { serviceClient } from '../../utils/supabase'

const PLACEHOLDER = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="220" height="140" viewBox="0 0 220 140">
  <rect width="220" height="140" fill="#eee" stroke="#999"/>
  <text x="110" y="75" text-anchor="middle" fill="#555" font-family="Georgia, serif" font-size="14">To be approved</text>
</svg>`

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id') || ''
  const db = serviceClient()
  if (!db || !id) throw createError({ statusCode: 404, statusMessage: 'Not found' })

  const { data: row } = await db.from('wiki_images').select('status, storage_path, mime').eq('id', id).maybeSingle()
  if (!row || row.status === 'rejected') {
    throw createError({ statusCode: 404, statusMessage: 'Not found' })
  }

  if (row.status === 'pending') {
    setHeader(event, 'content-type', 'image/svg+xml')
    setHeader(event, 'cache-control', 'no-store')
    return PLACEHOLDER
  }

  const { data: file, error } = await db.storage.from('wiki').download(row.storage_path)
  if (error || !file) {
    throw createError({ statusCode: 404, statusMessage: 'Not found' })
  }
  setHeader(event, 'content-type', row.mime || 'image/jpeg')
  setHeader(event, 'cache-control', 'public, max-age=86400')
  return Buffer.from(await file.arrayBuffer())
})
