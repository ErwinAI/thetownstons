import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { findWikiMatch } from '#shared/wiki'

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

export function findWikiPage(pathOrSlug: string): WikiPage | undefined {
  return findWikiMatch(pathOrSlug, allWikiPages())
}

export function listWikiPages(): WikiListItem[] {
  return allWikiPages().map(({ html, images, ...item }) => item)
}
