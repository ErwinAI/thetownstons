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
  return SLUG_ALIASES[text] || text
}

/** Old wiki titles that 404 but have a recovered page under another name. */
const SLUG_ALIASES: Record<string, string> = {
  shrines: 'attribute shrine',
  shrine: 'attribute shrine',
  "abaddon's handy candy boomstick": "abaddon's handy candy broomstick",
  "nai's flak jacket": "naj's flak jacket",
  "najas flak jacket": "naj's flak jacket",
  "doc wyvern's boots": "doc wyvern's",
  "sissirat's brother's cousin's roommate's staff of something really awesome":
    "sissirat's brother's cousin's roomate's staff of something really awesome",
  azzaz: "azza zin",
  "azza zins": "azza zin",
  "azzazin": "azza zin",
  "love/hate (mostly hate)": "love hate (mostly hate)",
  "love hate mostly hate": "love hate (mostly hate)",
  "king's coin": "king's coins",
  "kings coin": "king's coins",
  "kings coins": "king's coins",
}

/** Path chars that browsers, Vue Router, and static hosts treat as syntax. */
const UNSAFE_SLUG = /[?#\[\]@!$&'()*+,;=%.]/g

export function encodeWikiSlug(slug: string): string {
  return slug.split('/').map((part) => part.replace(UNSAFE_SLUG, encodeURIComponent)).join('/')
}

/** Safe /wiki/... href. Keeps slashes (Daily_Deed/_Storeroom) and encodes the rest. */
export function wikiHref(pathOrSlug: string): string {
  let slug = pathOrSlug.replace(/^\/wiki\//, '')
  try {
    slug = decodeURIComponent(slug)
  }
  catch {
    // keep raw
  }
  return `/wiki/${encodeWikiSlug(slug)}`
}

/** If `?` is part of the title (Travelers?_Check), not a query string (`?utm=`). */
export function mergeQuestionTitle(pathname: string, search: string): string {
  const query = (search || '').replace(/^\?/, '')
  if (!query || query.includes('=')) return pathname
  return `${pathname}?${query}`
}

/** Encode reserved chars in wiki hrefs so Algor's / Part 2 / Travelers? never get chopped. */
export function sanitizeWikiHtml(html: string): string {
  return html.replace(/\b(href|src)="(\/wiki\/[^"]*)"/gi, (_all, attr: string, url: string) => {
    return `${attr}="${wikiHref(url)}"`
  })
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
