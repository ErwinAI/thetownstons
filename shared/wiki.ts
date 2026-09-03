export type WikiLookup = {
  title: string
  wikiTitle: string
  path: string
}

function titleKey(value: string): string {
  const trimmed = value.replace(/^\/wiki\//, '')
  try {
    return decodeURIComponent(trimmed)
  }
  catch {
    return trimmed
  }
}

/** MediaWiki-ish fold: case, spaces/underscores, Category: vs Category/. */
export function foldWikiKey(value: string): string {
  let text = titleKey(value).replace(/_/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase()
  if (text.startsWith('category/')) text = `category:${text.slice('category/'.length)}`
  return text
}

export function isCategoryPage(page: WikiLookup): boolean {
  return foldWikiKey(page.wikiTitle).startsWith('category:')
    || foldWikiKey(page.path).startsWith('category:')
}

export function pageLookupKeys(page: WikiLookup): string[] {
  const keys = [foldWikiKey(page.wikiTitle), foldWikiKey(page.path), foldWikiKey(page.title)]
  if (!isCategoryPage(page)) return keys
  const extra: string[] = []
  for (const key of keys) {
    if (key.startsWith('category:')) extra.push(key.slice('category:'.length).trim())
  }
  return [...keys, ...extra]
}

export function findWikiMatch<T extends WikiLookup>(slug: string, pages: T[] | null | undefined): T | undefined {
  if (!pages?.length) return undefined
  const want = foldWikiKey(slug)
  if (!want) return undefined
  const matches = pages.filter((page) => pageLookupKeys(page).includes(want))
  if (!matches.length) return undefined
  if (want.startsWith('category:')) {
    return matches.find((page) => isCategoryPage(page)) || matches[0]
  }
  const stub = matches.find((page) => !isCategoryPage(page) && foldWikiKey(page.title).startsWith('category:'))
  if (stub) return matches.find((page) => isCategoryPage(page)) || stub
  return matches.find((page) => foldWikiKey(page.path) === want || foldWikiKey(page.wikiTitle) === want) || matches[0]
}

export function findCanonicalPath(slug: string, pages: WikiLookup[] | null | undefined): string | undefined {
  return findWikiMatch(slug, pages)?.path
}

export function wikiApiPath(wikiPath: string): string {
  const slug = wikiPath.replace(/^\/wiki\//, '').replace(/\/+$/, '')
  return `/api/wiki/${slug.split('/').map(encodeURIComponent).join('/')}`
}
