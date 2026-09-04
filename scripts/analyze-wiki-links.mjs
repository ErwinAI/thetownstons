import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

function titleKey(value) {
  const trimmed = value.replace(/^\/wiki\//, '')
  try {
    return decodeURIComponent(trimmed)
  }
  catch {
    return trimmed
  }
}

function foldWikiKey(value) {
  let text = titleKey(value).replace(/_/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase()
  if (text.startsWith('category/')) text = `category:${text.slice('category/'.length)}`
  return text
}

function isCategoryPage(page) {
  return foldWikiKey(page.wikiTitle).startsWith('category:')
    || foldWikiKey(page.path).startsWith('category:')
}

function pageLookupKeys(page) {
  const keys = [foldWikiKey(page.wikiTitle), foldWikiKey(page.path), foldWikiKey(page.title)]
  if (!isCategoryPage(page)) return keys
  const extra = []
  for (const key of keys) {
    if (key.startsWith('category:')) extra.push(key.slice('category:'.length).trim())
  }
  return [...keys, ...extra]
}

function findWikiMatch(slug, pages) {
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

function walk(dir, acc) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) {
      walk(full, acc)
      continue
    }
    if (!name.endsWith('.json')) continue
    const page = JSON.parse(readFileSync(full, 'utf8'))
    if (page?.path && page.title) acc.push(page)
  }
}

const pages = []
walk('content/wiki', pages)

const categoryMembers = new Map()
for (const p of pages) {
  for (const c of p.categories || []) {
    const key = c.toLowerCase().replace(/_/g, ' ')
    if (!categoryMembers.has(key)) categoryMembers.set(key, [])
    categoryMembers.get(key).push(p)
  }
}

function parseCategoryName(slug) {
  const raw = slug.replace(/^\/wiki\//, '').replace(/\/+$/, '')
  if (raw.startsWith('Category:')) return raw.slice('Category:'.length).replace(/_/g, ' ')
  if (raw.startsWith('Category/')) return raw.slice('Category/'.length).replace(/_/g, ' ')
  return ''
}

function resolves(href) {
  const slug = href.split('#')[0]
  if (!slug.startsWith('/wiki/')) return { ok: true, reason: 'not-wiki' }
  let bare = slug.replace(/^\/wiki\//, '').replace(/\/+$/, '')
  try {
    bare = decodeURIComponent(bare)
  }
  catch {
    // keep
  }

  const page = findWikiMatch(bare, pages)
  if (page) return { ok: true, reason: 'page', path: page.path }

  const catName = parseCategoryName(slug)
  if (catName) {
    const want = catName.toLowerCase().replace(/_/g, ' ')
    const members = categoryMembers.get(want) || []
    return { ok: true, reason: 'category-virtual', members: members.length }
  }
  return { ok: false, slug: bare, href }
}

const hrefRe = /href=["'](\/wiki\/[^"'#]+)/gi
const allLinks = new Map()
let totalLinks = 0

for (const p of pages) {
  const html = p.html || ''
  let m
  while ((m = hrefRe.exec(html)) !== null) {
    const href = m[1]
    totalLinks++
    const key = href.split('#')[0]
    if (!allLinks.has(key)) allLinks.set(key, { count: 0, sources: new Set() })
    const entry = allLinks.get(key)
    entry.count++
    if (entry.sources.size < 5) entry.sources.add(p.path)
  }
}

const broken = []
for (const [href, meta] of allLinks) {
  const r = resolves(href)
  if (!r.ok) {
    broken.push({
      href,
      folded: foldWikiKey(href),
      count: meta.count,
      sources: [...meta.sources],
    })
  }
}
broken.sort((a, b) => b.count - a.count)

function classify(href, folded) {
  const slug = href.replace(/^\/wiki\//, '')
  if (/^(Special|Talk|User|Category_talk|File|Image|MediaWiki|Help_talk|Template|Guild)/i.test(slug)) {
    return 'mediawiki-namespace'
  }
  if (slug.includes(':') && !/^Category:/i.test(slug)) return 'colon-namespace'
  if (/^Category:/i.test(slug) && !/^Category\//i.test(slug)) return 'category-colon-url'
  if (/^Category\//i.test(slug)) return 'missing-category-json'

  const exactPage = pages.find((p) => p.path === href || p.path === `/wiki/${slug}`)
  if (exactPage) return 'should-resolve'

  const byFold = pages.filter((p) =>
    pageLookupKeys(p).includes(folded) || foldWikiKey(p.path) === folded,
  )
  if (byFold.length) return 'case-or-canonical-mismatch'

  const asCat = slug.replace(/^Category[/:]/i, '').replace(/_/g, ' ').toLowerCase()
  if (categoryMembers.has(asCat)) return 'category-linked-as-article'

  if (/%[0-9A-F]{2}/i.test(slug)) return 'encoding'
  try {
    if (/[''()]/.test(decodeURIComponent(slug))) return 'punctuation'
  }
  catch {
    // keep going
  }

  return 'missing-page'
}

const groups = {}
for (const b of broken) {
  const g = classify(b.href, b.folded)
  if (!groups[g]) groups[g] = []
  groups[g].push(b)
}
for (const g of Object.keys(groups)) groups[g].sort((a, b) => b.count - a.count)

console.log('=== STATS ===')
console.log('Total pages:', pages.length)
console.log('Total wiki hrefs (with dupes):', totalLinks)
console.log('Unique wiki href targets:', allLinks.size)
console.log('Unique broken targets:', broken.length)
console.log('Broken href occurrences:', broken.reduce((s, b) => s + b.count, 0))

console.log('\n=== BROKEN BY CAUSE ===')
const sortedGroups = Object.entries(groups).sort(
  (a, b) => b[1].reduce((s, x) => s + x.count, 0) - a[1].reduce((s, x) => s + x.count, 0),
)
for (const [g, items] of sortedGroups) {
  const refs = items.reduce((s, x) => s + x.count, 0)
  console.log(`\n## ${g} (${items.length} unique, ${refs} refs)`)
  for (const item of items.slice(0, 30)) {
    console.log(`  ${item.count}x ${item.href} <- ${item.sources.join(', ')}`)
  }
}

const priority = [
  'Skills', 'Fighter_Armor', 'Mage_Armor', 'Ranger_Armor', 'Relic_Quests',
  'Quest_Items_List', 'Main_Page', 'Newbie_Guide', 'Boss_Guide',
  'One-Handed-mage', 'Two-Handed-mage', 'One-Handed-fighter', 'Two-Handed-fighter',
  'Two-Handed-ranger', 'Weapons', 'Armour', 'Items', 'Level_100_Boss_Guide',
]
console.log('\n=== PRIORITY PAGE BROKEN LINKS ===')
for (const name of priority) {
  const p = findWikiMatch(name, pages)
  if (!p) {
    console.log(`\n${name}: PAGE NOT FOUND`)
    continue
  }
  const html = p.html || ''
  const links = [...html.matchAll(hrefRe)].map((m) => m[1])
  const uniqueBroken = [...new Set(links.filter((h) => !resolves(h).ok))]
  console.log(`\n${p.title} (${p.path}): ${links.length} links, ${uniqueBroken.length} broken unique`)
  for (const h of uniqueBroken) console.log(`  ${h}`)
}

console.log('\n=== CATEGORIES WITH MEMBERS BUT NO CATEGORY JSON ===')
const categoryPageNames = new Set(
  pages.filter(isCategoryPage).map((p) => parseCategoryName(p.path).toLowerCase().replace(/_/g, ' ')),
)
const virtualOnly = []
for (const [cat, members] of categoryMembers) {
  if (!categoryPageNames.has(cat) && members.length > 0) {
    virtualOnly.push({ cat, count: members.length })
  }
}
virtualOnly.sort((a, b) => b.count - a.count)
console.log('Count:', virtualOnly.length)
for (const v of virtualOnly.slice(0, 40)) {
  console.log(`  ${v.count} members: ${v.cat}`)
}

const idx = pages.find((p) => p.path === '/wiki/index.html')
console.log('\n=== index.html.json ===')
console.log('In catalog:', !!idx)
if (idx) {
  const links = [...(idx.html || '').matchAll(hrefRe)].map((m) => m[1])
  for (const h of links) {
    const r = resolves(h)
    console.log(`  ${h}: ${r.ok ? 'OK (' + r.reason + ')' : 'BROKEN'}`)
  }
}

console.log('\n=== FILE PATH vs page.path MISMATCHES (Linux case traps) ===')
const fileTraps = []
function walkFiles(dir) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) {
      walkFiles(full)
      continue
    }
    if (!name.endsWith('.json')) continue
    const rel = relative('content/wiki', full).replace(/\\/g, '/')
    const page = JSON.parse(readFileSync(full, 'utf8'))
    const pathSlug = (page.path || '').replace(/^\/wiki\//, '')
    const fileSlug = rel.replace(/\.json$/, '')
    if (fileSlug !== pathSlug) {
      fileTraps.push({ file: rel, pathSlug, fileSlug, path: page.path })
    }
  }
}
walkFiles('content/wiki')
console.log('Count:', fileTraps.length)
for (const t of fileTraps.slice(0, 50)) {
  console.log(`  file:${t.file} -> path:${t.path}`)
}

console.log('\n=== TOP 80 BROKEN (by ref count) ===')
for (const b of broken.slice(0, 80)) {
  console.log(`${b.count}x [${classify(b.href, b.folded)}] ${b.href}`)
}

// Category 404 simulation: URLs that look like categories but have no page and no members
console.log('\n=== CATEGORY URLS THAT WOULD 404 (no page, no members) ===')
const catUrls = new Set()
for (const [href] of allLinks) {
  const slug = href.replace(/^\/wiki\//, '')
  if (/^Category[/:]/i.test(slug)) catUrls.add(href.split('#')[0])
}
const deadCats = []
for (const href of catUrls) {
  const r = resolves(href)
  if (!r.ok) deadCats.push(href)
  else if (r.reason === 'category-virtual' && r.members === 0) deadCats.push(href + ' (0 members)')
}
console.log('Dead category URLs from links:', deadCats.length)
for (const d of deadCats.slice(0, 30)) console.log('  ' + d)
