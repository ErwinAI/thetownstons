import { mergeCategoryNames, mergeQuestionTitle } from '#shared/wiki'
import { extractWikiCategories, renderWikiMarkdown } from '#shared/wiki-md'
import { saveWikiPage } from '../../utils/wiki-db'
import { assertEmailConfirmed } from '../../utils/access'
import { userFromRequest } from '../../utils/supabase'

export default defineEventHandler(async (event) => {
  const user = await userFromRequest(event)
  if (!user) {
    throw createError({ statusCode: 401, statusMessage: 'Log in to edit' })
  }
  assertEmailConfirmed(user)

  const slug = (getRouterParam(event, 'slug') || '').replace(/\/+$/, '')
  const full = (event.node?.req?.url || event.path || '').replace(/^\/api\/wiki\//, '')
  const q = full.indexOf('?')
  const pathOnly = (q >= 0 ? full.slice(0, q) : full).replace(/\/+$/, '')
  const search = q >= 0 ? full.slice(q) : ''
  const raw = mergeQuestionTitle(pathOnly, search)
  let decoded = raw
  try {
    decoded = decodeURIComponent(raw)
  }
  catch {
    decoded = raw
  }

  const body = await readBody<{ title?: string, body_md?: string, categories?: string[] }>(event)
  const title = String(body?.title || '').trim()
  const pulled = extractWikiCategories(String(body?.body_md || ''))
  const bodyMd = pulled.text
  if (!title) {
    throw createError({ statusCode: 400, statusMessage: 'Title is required' })
  }

  return saveWikiPage({
    slug: decoded || slug,
    title,
    html: renderWikiMarkdown(bodyMd),
    body_md: bodyMd,
    categories: mergeCategoryNames(body?.categories, pulled.categories),
    editor: user.email || user.id,
    editorId: user.id,
  })
})
