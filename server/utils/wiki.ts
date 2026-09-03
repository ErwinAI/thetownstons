import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

export type WikiPage = {
  title: string
  wikiTitle: string
  path: string
  description?: string
  categories: string[]
  images: string[]
  html: string
}

export type WikiListItem = Pick<WikiPage, 'title' | 'wikiTitle' | 'path' | 'description' | 'categories'>

let cache: WikiPage[] | null = null // rebuild when content/wiki changes

function walk(dir: string, acc: WikiPage[]) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) {
      walk(full, acc)
      continue
    }
    if (!name.endsWith('.json')) continue
    const page = JSON.parse(readFileSync(full, 'utf8')) as WikiPage
    if (page?.path && page.title) acc.push(page)
  }
}

export function allWikiPages(): WikiPage[] {
  if (!cache) {
    cache = []
    walk(join(process.cwd(), 'content/wiki'), cache)
    cache.sort((a, b) => a.title.localeCompare(b.title))
  }
  return cache
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
function normKey(value: string): string {
  let text = titleKey(value).replace(/_/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase()
  if (text.startsWith('category/')) text = `category:${text.slice('category/'.length)}`
  return text
}

function pageKeys(page: WikiPage): string[] {
  const keys = [normKey(page.wikiTitle), normKey(page.path), normKey(page.title)]
  const extra: string[] = []
  for (const key of keys) {
    if (key.startsWith('category:')) extra.push(key.slice('category:'.length).trim())
    else extra.push(`category:${key}`)
  }
  return [...keys, ...extra]
}

export function findWikiPage(pathOrSlug: string): WikiPage | undefined {
  const want = normKey(pathOrSlug)
  if (!want) return undefined
  const matches = allWikiPages().filter((page) => pageKeys(page).includes(want))
  if (!matches.length) return undefined
  if (want.startsWith('category:')) {
    return matches.find((page) => normKey(page.wikiTitle).startsWith('category:'))
      || matches.find((page) => normKey(page.title).startsWith('category:'))
      || matches[0]
  }
  return matches[0]
}

export function listWikiPages(): WikiListItem[] {
  return allWikiPages().map(({ html, images, ...item }) => item)
}
