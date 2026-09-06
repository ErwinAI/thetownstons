import { findWikiPage, listWikiPages, allWikiPages, type WikiPage } from './wiki'
import { foldWikiKey, isCategoryPage, normalizeWikiPath, type WikiLookup } from '#shared/wiki'
import { htmlToWikiMarkdown } from '#shared/html-to-md'
import { lineDiff } from '#shared/text-diff'
import { assertCanEdit } from './access'
import { serviceClient } from './supabase'

export type WikiApiPage = WikiPage & {
  slug?: string
  body_md?: string | null
  wiki_title?: string
}

type PageRow = {
  slug: string
  fold_key: string
  title: string
  wiki_title: string
  path: string
  description: string | null
  html: string
  body_md: string | null
  categories: string[] | null
  images: string[] | null
  locked?: boolean
  updated_by?: string | null
}

function fromRow(row: PageRow): WikiApiPage {
  return {
    slug: row.slug,
    title: row.title,
    wikiTitle: row.wiki_title,
    wiki_title: row.wiki_title,
    path: row.path,
    description: row.description || undefined,
    html: row.html || '',
    body_md: row.body_md,
    categories: row.categories || [],
    images: row.images || [],
  }
}

function fromFile(page: WikiPage): WikiApiPage {
  return { ...page, body_md: null, wiki_title: page.wikiTitle }
}

function slugVariants(raw: string): string[] {
  let decoded = raw
  try {
    decoded = decodeURIComponent(raw)
  }
  catch {
    decoded = raw
  }
  const trimmed = decoded.replace(/^\/wiki\//, '').replace(/\/+$/, '')
  const underscored = trimmed.replace(/ /g, '_')
  const spaced = trimmed.replace(/_/g, ' ')
  const variants = new Set([trimmed, underscored, spaced])
  if (underscored.startsWith('Category:')) variants.add('Category/' + underscored.slice('Category:'.length))
  if (underscored.startsWith('Category/')) variants.add('Category:' + underscored.slice('Category/'.length))
  return [...variants].filter(Boolean)
}

export async function resolveWikiPage(raw: string): Promise<WikiApiPage | undefined> {
  const db = serviceClient()
  if (db) {
    const variants = slugVariants(raw)
    const { data: exact } = await db.from('pages').select('*').in('slug', variants).limit(1)
    if (exact?.[0]) return fromRow(exact[0] as PageRow)

    const folded = normalizeWikiPath(raw)
    if (folded) {
      const { data: byFold } = await db.from('pages').select('*').eq('fold_key', folded).limit(1).maybeSingle()
      if (byFold) return fromRow(byFold as PageRow)

      const aliased = foldWikiKey(raw)
      if (aliased !== folded) {
        const { data: byAliasFold } = await db.from('pages').select('*').eq('fold_key', aliased).limit(1).maybeSingle()
        if (byAliasFold) return fromRow(byAliasFold as PageRow)
      }

      const { data: alias } = await db.from('page_aliases').select('slug').eq('alias', folded).maybeSingle()
      if (alias?.slug) {
        const { data: target } = await db.from('pages').select('*').eq('slug', alias.slug).maybeSingle()
        if (target) return fromRow(target as PageRow)
      }
    }
  }

  const file = findWikiPage(raw)
  return file ? fromFile(file) : undefined
}

export async function listWikiSummaries() {
  const db = serviceClient()
  if (db) {
    const { data, error } = await db
      .from('pages')
      .select('title, wiki_title, path, description, categories')
      .order('title')
    if (!error && data) {
      return data.map((row) => ({
        title: row.title,
        wikiTitle: row.wiki_title,
        path: row.path,
        description: row.description || undefined,
        categories: row.categories || [],
      }))
    }
  }
  return listWikiPages()
}

export async function randomWikiPath(): Promise<string | undefined> {
  const db = serviceClient()
  if (db) {
    const { data } = await db.rpc('random_page_path')
    if (typeof data === 'string' && data) return data
  }
  const pages = allWikiPages().filter((page) => !isCategoryPage(page))
  if (!pages.length) return undefined
  return pages[Math.floor(Math.random() * pages.length)]!.path
}

function foldCat(value: string): string {
  return value.replace(/_/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase()
}

function fileCategoryLists(name: string): { members: WikiLookup[], subcats: WikiLookup[] } {
  const want = foldCat(name)
  const members: WikiLookup[] = []
  const subcats: WikiLookup[] = []
  for (const page of allWikiPages()) {
    if (!(page.categories || []).some((cat) => foldCat(cat) === want)) continue
    const item = { title: page.title, wikiTitle: page.wikiTitle, path: page.path }
    if (isCategoryPage(page)) subcats.push(item)
    else members.push(item)
  }
  return { members, subcats }
}

export async function categoryLists(name: string): Promise<{ members: WikiLookup[], subcats: WikiLookup[] }> {
  const db = serviceClient()
  if (db) {
    const { data, error } = await db.rpc('category_lists', { cat: name })
    if (!error && Array.isArray(data)) {
      const members: WikiLookup[] = []
      const subcats: WikiLookup[] = []
      for (const row of data as { kind: string, title: string, path: string }[]) {
        const item = { title: row.title, wikiTitle: row.title, path: row.path }
        if (row.kind === 'subcat') subcats.push(item)
        else members.push(item)
      }
      return { members, subcats }
    }
  }
  return fileCategoryLists(name)
}

export async function saveWikiPage(input: {
  slug: string
  title: string
  html: string
  body_md: string
  categories?: string[]
  editor?: string | null
  editorId?: string | null
}): Promise<WikiApiPage> {
  const db = serviceClient()
  if (!db) {
    throw createError({ statusCode: 503, statusMessage: 'Wiki store is not configured' })
  }
  const slug = slugVariants(input.slug)[0] || input.slug
  const { data: existing } = await db.from('pages').select('*').eq('slug', slug).maybeSingle()
  const prior = existing as PageRow | null
  if (!input.editorId) {
    throw createError({ statusCode: 401, statusMessage: 'Log in to edit' })
  }
  const profile = await assertCanEdit(input.editorId, prior?.locked)
  const editorName = profile.username || input.editor || null
  const path = prior?.path || (slug.startsWith('/') ? slug : `/wiki/${slug}`)
  const wikiTitle = prior?.wiki_title || slug.replace(/^Category\//, 'Category:')
  const row = {
    slug,
    fold_key: prior?.fold_key || normalizeWikiPath(slug),
    title: input.title,
    wiki_title: wikiTitle,
    path,
    description: prior?.description || null,
    html: input.html,
    body_md: input.body_md,
    categories: input.categories ?? prior?.categories ?? [],
    images: prior?.images || [],
    updated_at: new Date().toISOString(),
    updated_by: input.editorId || prior?.updated_by || null,
    locked: prior?.locked ?? false,
  }
  if (prior) {
    const { count } = await db.from('page_revisions').select('id', { count: 'exact', head: true }).eq('slug', slug)
    if (!count) {
      await db.from('page_revisions').insert({
        slug,
        title: prior.title,
        html: prior.html,
        body_md: prior.body_md,
        editor: 'recovered',
        editor_id: null,
      })
    }
  }

  const { data, error } = await db.from('pages').upsert(row, { onConflict: 'slug' }).select('*').single()
  if (error || !data) {
    throw createError({ statusCode: 500, statusMessage: error?.message || 'Save failed' })
  }
  await db.from('page_revisions').insert({
    slug,
    title: input.title,
    html: input.html,
    body_md: input.body_md,
    editor: editorName,
    editor_id: input.editorId || null,
  })
  return fromRow(data as PageRow)
}

export type WikiRevision = {
  id: number
  slug: string
  title: string
  html: string
  body_md: string | null
  editor: string | null
  created_at: string
}

async function usernamesById(db: NonNullable<ReturnType<typeof serviceClient>>, ids: string[]) {
  const unique = [...new Set(ids.filter(Boolean))]
  if (!unique.length) return new Map<string, string>()
  const { data } = await db.from('users').select('id, username').in('id', unique)
  return new Map((data || []).map((row) => [row.id as string, row.username as string]))
}

function editorLabel(editor: string | null, editorId: string | null | undefined, names: Map<string, string>) {
  if (editorId && names.get(editorId)) return names.get(editorId)!
  if (editor && !editor.includes('@')) return editor
  return editorId ? 'user' : (editor || '—')
}

export async function listWikiRevisions(raw: string): Promise<{ page?: WikiApiPage, revisions: Omit<WikiRevision, 'html' | 'body_md'>[] }> {
  const page = await resolveWikiPage(raw)
  const db = serviceClient()
  if (!db || !page?.slug) return { page, revisions: [] }
  const { data, error } = await db
    .from('page_revisions')
    .select('id, slug, title, editor, editor_id, created_at')
    .eq('slug', page.slug)
    .order('created_at', { ascending: false })
  if (error || !data) return { page, revisions: [] }
  const names = await usernamesById(db, data.map((row) => row.editor_id as string).filter(Boolean))
  return {
    page,
    revisions: data.map((row) => ({
      id: row.id,
      slug: row.slug,
      title: row.title,
      editor: editorLabel(row.editor, row.editor_id, names),
      created_at: row.created_at,
    })),
  }
}

export async function listRecentChanges(opts: { user?: string, limit?: number } = {}) {
  const db = serviceClient()
  if (!db) return []
  const limit = Math.min(Math.max(opts.limit || 80, 1), 200)
  let editorId: string | undefined
  if (opts.user) {
    const { data: profile } = await db.from('users').select('id').ilike('username', opts.user).maybeSingle()
    if (!profile?.id) return []
    editorId = profile.id
  }
  let query = db
    .from('page_revisions')
    .select('id, slug, title, editor, editor_id, created_at')
    .order('created_at', { ascending: false })
    .limit(limit)
  if (editorId) query = query.eq('editor_id', editorId)
  const { data, error } = await query
  if (error || !data) return []
  const names = await usernamesById(db, data.map((row) => row.editor_id as string).filter(Boolean))
  return data.map((row) => ({
    id: row.id as number,
    slug: row.slug as string,
    title: row.title as string,
    path: `/wiki/${row.slug}`,
    editor: editorLabel(row.editor as string | null, row.editor_id as string | null, names),
    created_at: row.created_at as string,
  }))
}

function revisionSource(rev: Pick<WikiRevision, 'body_md' | 'html'>): string {
  if (rev.body_md && !/^\s*</.test(rev.body_md)) return rev.body_md
  return htmlToWikiMarkdown(rev.html || rev.body_md || '')
}

export async function diffWikiRevision(raw: string, id: number) {
  const current = await getWikiRevision(raw, id)
  if (!current) {
    throw createError({ statusCode: 404, statusMessage: 'Revision not found' })
  }
  const db = serviceClient()
  if (!db) {
    throw createError({ statusCode: 503, statusMessage: 'Wiki store is not configured' })
  }
  const { data: prior } = await db
    .from('page_revisions')
    .select('*')
    .eq('slug', current.slug)
    .lt('created_at', current.created_at)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle()
  const before = prior ? revisionSource(prior as WikiRevision) : ''
  const after = revisionSource(current)
  return {
    revision: {
      id: current.id,
      title: current.title,
      editor: current.editor,
      created_at: current.created_at,
    },
    before_title: prior ? (prior as WikiRevision).title : '',
    lines: lineDiff(before, after),
  }
}

export async function getWikiRevision(raw: string, id: number): Promise<WikiRevision | undefined> {
  const page = await resolveWikiPage(raw)
  const db = serviceClient()
  if (!db || !page?.slug || !id) return undefined
  const { data } = await db.from('page_revisions').select('*').eq('slug', page.slug).eq('id', id).maybeSingle()
  return data ? data as WikiRevision : undefined
}

export async function revertWikiPage(raw: string, id: number, editor?: string | null, editorId?: string | null): Promise<WikiApiPage> {
  const rev = await getWikiRevision(raw, id)
  if (!rev) {
    throw createError({ statusCode: 404, statusMessage: 'Revision not found' })
  }
  const page = await resolveWikiPage(raw)
  const bodyMd = rev.body_md || htmlToWikiMarkdown(rev.html || '')
  return saveWikiPage({
    slug: rev.slug,
    title: rev.title,
    html: rev.html,
    body_md: bodyMd,
    categories: page?.categories,
    editor: editor || null,
    editorId: editorId || null,
  })
}

export type WikiSearchHit = {
  title: string
  path: string
  rank: number
  headline: string
}

function stripHtml(value: string): string {
  return value.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
}

function snippetAround(text: string, q: string): string {
  const hay = text.toLowerCase()
  const needle = q.toLowerCase()
  const at = hay.indexOf(needle)
  if (at < 0) return text.slice(0, 180)
  const start = Math.max(0, at - 60)
  const chunk = text.slice(start, start + 180)
  return (start > 0 ? '…' : '') + chunk + (start + 180 < text.length ? '…' : '')
}

export async function searchWiki(q: string): Promise<WikiSearchHit[]> {
  const query = q.replace(/\s+/g, ' ').trim()
  if (query.length < 2) return []

  const db = serviceClient()
  if (db) {
    const { data, error } = await db.rpc('search_wiki', { q: query, max_rows: 50 })
    if (!error && Array.isArray(data)) {
      return (data as { title: string, path: string, rank: number, headline: string }[]).map((row) => ({
        title: row.title,
        path: row.path,
        rank: Number(row.rank) || 0,
        headline: String(row.headline || '').replace(/<(?!\/?b\b)[^>]*>/gi, ''),
      }))
    }

    const like = query.replace(/[%_,.()"'\\]/g, ' ').replace(/\s+/g, ' ').trim()
    if (like.length >= 2) {
      const { data: rows } = await db
        .from('pages')
        .select('title, path, html, body_md')
        .or(`title.ilike.%${like}%,html.ilike.%${like}%,body_md.ilike.%${like}%`)
        .limit(50)
      if (rows?.length) {
        return rows.map((row) => {
          const text = stripHtml(row.body_md || row.html || '')
          return {
            title: row.title,
            path: row.path,
            rank: String(row.title).toLowerCase().includes(like.toLowerCase()) ? 1 : 0,
            headline: snippetAround(text, like),
          }
        })
      }
    }
  }

  const needle = query.toLowerCase()
  return allWikiPages()
    .filter((page) => {
      const blob = `${page.title}\n${page.description || ''}\n${stripHtml(page.html || '')}`.toLowerCase()
      return blob.includes(needle)
    })
    .slice(0, 50)
    .map((page) => ({
      title: page.title,
      path: page.path,
      rank: page.title.toLowerCase().includes(needle) ? 1 : 0,
      headline: snippetAround(stripHtml(page.html || ''), query),
    }))
}
