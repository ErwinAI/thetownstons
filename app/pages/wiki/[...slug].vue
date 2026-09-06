<script setup lang="ts">
import { decodeWikiSlug, mergeQuestionTitle, normalizeWikiPath, sanitizeWikiHtml, wikiApiPath, wikiHref, wikiRequestNeedsCanonical } from '#shared/wiki'

const route = useRoute()
const { user } = useAuth()
const { canEdit } = useWikiAccess()
const karlPage = useKarlPage()

const slug = computed(() => {
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
  path = decodeWikiSlug(path)
  path = mergeQuestionTitle(path, search)
  if (path) return path
  const parts = route.params.slug
  return Array.isArray(parts) ? parts.join('/') : String(parts || '')
})

const requestPath = computed(() => `/wiki/${slug.value}`)

if (normalizeWikiPath(slug.value) === 'main page') {
  await navigateTo('/', { redirectCode: 301, replace: true })
}

const { data: page } = await useAsyncData(
  () => 'wiki-' + slug.value,
  () => $fetch(wikiApiPath(requestPath.value)).catch(() => null),
)

if (page.value?.path && wikiRequestNeedsCanonical(requestPath.value, page.value.path)) {
  await navigateTo(wikiHref(page.value.path), { redirectCode: 301, replace: true })
}

const apiSlug = computed(() => (page.value?.path || requestPath.value).replace(/^\/wiki\//, ''))

const categoryName = computed(() => {
  const raw = apiSlug.value
  if (raw.startsWith('Category:')) return raw.slice('Category:'.length).replace(/_/g, ' ')
  if (raw.startsWith('Category/')) return raw.slice('Category/'.length).replace(/_/g, ' ')
  return ''
})

const { data: lists } = await useAsyncData(
  () => 'cat-' + categoryName.value,
  () => categoryName.value
    ? $fetch('/api/category', { query: { name: categoryName.value } }).catch(() => ({ members: [], subcats: [] }))
    : Promise.resolve({ members: [], subcats: [] }),
)

const members = computed(() => lists.value?.members || [])
const subcats = computed(() => lists.value?.subcats || [])

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

const missing = computed(() => !page.value && !members.value.length && !categoryName.value)

if (missing.value && import.meta.server) {
  const event = useRequestEvent()
  if (event) setResponseStatus(event, 404)
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

const editTo = computed(() => '/edit/' + apiSlug.value)
const historyTo = computed(() => '/history/' + apiSlug.value)

watch([page, categoryName, requestPath], () => {
  if (page.value?.title && page.value.path) {
    karlPage.value = { title: page.value.title, path: page.value.path }
    return
  }
  if (categoryName.value) {
    karlPage.value = { title: `Category:${categoryName.value}`, path: requestPath.value }
    return
  }
  karlPage.value = null
}, { immediate: true })

onBeforeUnmount(() => {
  karlPage.value = null
})
</script>

<template>
  <article v-if="page">
    <WikiTitleBar :title="page.title" :history-to="historyTo" :edit-to="editTo" />
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
    <WikiTitleBar :title="'Category:' + categoryName" :history-to="historyTo" :edit-to="editTo" />
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
  <article v-else>
    <WikiTitleBar :title="decodeWikiSlug(slug).replace(/_/g, ' ')" :edit-to="editTo" />
    <div id="siteSub">From Townstons</div>
    <div class="wiki-body">
      <p>This page does not exist yet.</p>
      <p v-if="canEdit"><NuxtLink :to="editTo">Create this page</NuxtLink></p>
      <p v-else-if="user">Confirm your email, then you can create this page.</p>
      <p v-else><NuxtLink to="/login">Log in</NuxtLink> to create it, or <NuxtLink to="/signup">sign up</NuxtLink>.</p>
    </div>
  </article>
</template>
