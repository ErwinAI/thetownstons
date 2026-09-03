<script setup lang="ts">
import { findCanonicalPath, wikiApiPath } from '#shared/wiki'

const route = useRoute()
const slug = computed(() => {
  // Colons in titles (Category:Foo) get eaten as Vue/Nitro params.
  // Prefer the real request path, then fall back to the catch-all.
  let path = ''
  if (import.meta.server) {
    path = useRequestURL().pathname
  }
  else if (import.meta.client) {
    path = window.location.pathname
  }
  path = path.replace(/^\/wiki\//, '').replace(/\/+$/, '')
  try {
    path = decodeURIComponent(path)
  }
  catch {
    // keep raw
  }
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

if (canonicalPath.value && canonicalPath.value !== requestPath.value) {
  await navigateTo(canonicalPath.value, { redirectCode: 301, replace: true })
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

const members = computed(() => {
  if (!categoryName.value || !pages.value.length) return []
  const want = categoryName.value.toLowerCase().replace(/_/g, ' ')
  return pages.value.filter((item) =>
    (item.categories || []).some((c) => c.toLowerCase().replace(/_/g, ' ') === want),
  )
})

if (!page.value && !members.value.length && !categoryName.value) {
  throw createError({ statusCode: 404, statusMessage: 'Page not found', fatal: true })
}

useHead({ title: page.value?.title || categoryName.value || 'Wiki' })

const categories = computed(() => page.value?.categories ?? [])
</script>

<template>
  <article v-if="page">
    <h1 class="firstHeading">{{ page.title }}</h1>
    <div id="siteSub">From Townstons</div>
    <div class="wiki-body" v-html="page.html" />
    <div v-if="categories.length" class="catlinks">
      Categories:
      <template v-for="(cat, i) in categories" :key="cat">
        <NuxtLink :to="'/wiki/Category/' + cat.replace(/ /g, '_')">{{ cat }}</NuxtLink>
        <span v-if="i < categories.length - 1"> | </span>
      </template>
    </div>
    <div v-if="categoryName && members.length" class="wiki-body">
      <h2>Pages in this category</h2>
      <ul>
        <li v-for="member in members" :key="member.path">
          <NuxtLink :to="member.path">{{ member.title }}</NuxtLink>
        </li>
      </ul>
    </div>
  </article>
  <article v-else-if="categoryName">
    <h1 class="firstHeading">Category:{{ categoryName }}</h1>
    <div id="siteSub">From Townstons</div>
    <div class="wiki-body">
      <p v-if="!members.length">No recovered pages in this category yet.</p>
      <ul>
        <li v-for="member in members" :key="member.path">
          <NuxtLink :to="member.path">{{ member.title }}</NuxtLink>
        </li>
      </ul>
    </div>
  </article>
</template>
