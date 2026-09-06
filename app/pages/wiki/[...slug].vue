<script setup lang="ts">
import { findCanonicalPath, isSameWikiPath, mergeQuestionTitle, sanitizeWikiHtml, wikiApiPath, wikiHref } from '#shared/wiki'

const route = useRoute()
const slug = computed(() => {
  // Colons in titles (Category:Foo) get eaten as Vue/Nitro params.
  // Prefer the real request path, then fall back to the catch-all.
  let path = ''
  let search = ''
  if (import.meta.server) {
    const url = useRequestURL()
    path = url.pathname
    search = url.search
  }
  else if (import.meta.client) {
    path = window.location.pathname
    search = window.location.search
  }
  path = path.replace(/^\/wiki\//, '').replace(/\/+$/, '')
  try {
    path = decodeURIComponent(path)
  }
  catch {
    // keep raw
  }
  path = mergeQuestionTitle(path, search)
  if (path) return path
  const parts = route.params.slug
  return Array.isArray(parts) ? parts.join('/') : String(parts || '')
})

const { data: catalog } = await useAsyncData('wiki-catalog', () =>
  $fetch('/api/pages').catch(() => []),
)

const pages = computed(() => Array.isArray(catalog.value) ? catalog.value : [])

const canonicalPath = computed(() => findCanonicalPath(slug.value, pages.value))
const requestPath = computed(() => `/wiki/${slug.value}`)
const targetPath = computed(() => canonicalPath.value || requestPath.value)

if (canonicalPath.value && !isSameWikiPath(canonicalPath.value, requestPath.value)) {
  await navigateTo(wikiHref(canonicalPath.value), { redirectCode: 301, replace: true })
}

const apiSlug = computed(() => targetPath.value.replace(/^\/wiki\//, ''))

const { data: page } = await useAsyncData(
  () => 'wiki-' + apiSlug.value,
  () => $fetch(wikiApiPath(targetPath.value)).catch(() => null),
)

const categoryName = computed(() => {
  const raw = apiSlug.value
  if (raw.startsWith('Category:')) return raw.slice('Category:'.length).replace(/_/g, ' ')
  if (raw.startsWith('Category/')) return raw.slice('Category/'.length).replace(/_/g, ' ')
  return ''
})

const GLOSSARY_IN_RAINBOW = new Set([
  'mythic suffixes',
  'growth items',
  'modifiers',
  'name descriptors',
  'kings coins',
  "king's coins",
  'soulbound',
  'loot',
  'items',
])

const members = computed(() => {
  if (!categoryName.value || !pages.value.length) return []
  const want = categoryName.value.toLowerCase().replace(/_/g, ' ')
  return pages.value.filter((item) => {
    if (String(item.title || '').startsWith('Category:')) return false
    if (want === 'rainbow items' && GLOSSARY_IN_RAINBOW.has(String(item.title || '').toLowerCase())) {
      return false
    }
    return (item.categories || []).some((c) => c.toLowerCase().replace(/_/g, ' ') === want)
  })
})

const subcats = computed(() => {
  if (!categoryName.value || !pages.value.length) return []
  const want = categoryName.value.toLowerCase().replace(/_/g, ' ')
  return pages.value
    .filter((item) => {
      if (!String(item.title || '').startsWith('Category:')) return false
      return (item.categories || []).some((c) => c.toLowerCase().replace(/_/g, ' ') === want)
    })
    .map((item) => ({
      ...item,
      title: String(item.title).replace(/^Category:/, ''),
    }))
    .sort((a, b) => a.title.localeCompare(b.title))
})

function alphaColumns<T extends { title: string }>(items: T[]) {
  const groups: { letter: string, items: T[] }[] = []
  for (const item of [...items].sort((a, b) => a.title.localeCompare(b.title))) {
    const raw = item.title.replace(/^[^A-Za-z0-9]+/, '')
    const letter = raw ? raw[0].toUpperCase() : '#'
    const last = groups[groups.length - 1]
    if (!last || last.letter !== letter) groups.push({ letter, items: [item] })
    else last.items.push(item)
  }
  const columns: typeof groups[] = [[], [], []]
  const counts = [0, 0, 0]
  for (const group of groups) {
    let col = 0
    if (counts[1] < counts[0]) col = 1
    if (counts[2] < counts[col]) col = 2
    columns[col].push(group)
    counts[col] += group.items.length
  }
  return columns
}

const memberGroups = computed(() => alphaColumns(members.value))
const subcatGroups = computed(() => alphaColumns(subcats.value))

if (!page.value && !members.value.length && !categoryName.value) {
  throw createError({ statusCode: 404, statusMessage: 'Page not found', fatal: true })
}

useHead({ title: page.value?.title || categoryName.value || 'Wiki' })

const categories = computed(() => page.value?.categories ?? [])
const bodyHtml = computed(() => sanitizeWikiHtml(page.value?.html || ''))
const displayHtml = computed(() => {
  let html = bodyHtml.value
  if (categoryName.value) {
    html = html.replace(/<div id="mw-pages">[\s\S]*?<\/div>/i, '')
    html = html.replace(/<div id="mw-subcategories">[\s\S]*?<\/div>/i, '')
  }
  return html
})
</script>

<template>
  <article v-if="page">
    <h1 class="firstHeading">{{ page.title }}</h1>
    <div id="siteSub">From Townstons</div>
    <div class="wiki-body" v-html="displayHtml" />
    <div v-if="categoryName && subcats.length" id="mw-subcategories" class="wiki-body">
      <h2>Subcategories</h2>
      <p>There {{ subcats.length === 1 ? 'is' : 'are' }} {{ subcats.length }} subcategor{{ subcats.length === 1 ? 'y' : 'ies' }} to this category.</p>
      <table class="wiki-cat-members" width="100%">
        <tr valign="top">
          <td v-for="(column, col) in subcatGroups" :key="'sub-' + col">
            <template v-for="group in column" :key="group.letter">
              <h3>{{ group.letter }}</h3>
              <ul>
                <li v-for="item in group.items" :key="item.path">
                  <NuxtLink :to="wikiHref(item.path)">{{ item.title }}</NuxtLink>
                </li>
              </ul>
            </template>
          </td>
        </tr>
      </table>
    </div>
    <div v-if="categoryName && members.length" id="mw-pages" class="wiki-body">
      <h2>Articles in category "{{ categoryName }}"</h2>
      <p>There {{ members.length === 1 ? 'is' : 'are' }} {{ members.length }} article{{ members.length === 1 ? '' : 's' }} in this category.</p>
      <table class="wiki-cat-members" width="100%">
        <tr valign="top">
          <td v-for="(column, col) in memberGroups" :key="col">
            <template v-for="group in column" :key="group.letter">
              <h3>{{ group.letter }}</h3>
              <ul>
                <li v-for="member in group.items" :key="member.path">
                  <NuxtLink :to="wikiHref(member.path)">{{ member.title }}</NuxtLink>
                </li>
              </ul>
            </template>
          </td>
        </tr>
      </table>
    </div>
    <div v-if="categories.length" class="catlinks">
      Categories:
      <template v-for="(cat, i) in categories" :key="cat">
        <NuxtLink :to="wikiHref('/wiki/Category/' + cat.replace(/ /g, '_'))">{{ cat }}</NuxtLink>
        <span v-if="i < categories.length - 1"> | </span>
      </template>
    </div>
  </article>
  <article v-else-if="categoryName">
    <h1 class="firstHeading">Category:{{ categoryName }}</h1>
    <div id="siteSub">From Townstons</div>
    <div class="wiki-body">
      <p v-if="!members.length">No recovered pages in this category yet.</p>
      <table v-else class="wiki-cat-members" width="100%">
        <tr valign="top">
          <td v-for="(column, col) in memberGroups" :key="col">
            <template v-for="group in column" :key="group.letter">
              <h3>{{ group.letter }}</h3>
              <ul>
                <li v-for="member in group.items" :key="member.path">
                  <NuxtLink :to="wikiHref(member.path)">{{ member.title }}</NuxtLink>
                </li>
              </ul>
            </template>
          </td>
        </tr>
      </table>
    </div>
  </article>
</template>
