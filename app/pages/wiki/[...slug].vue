<script setup lang="ts">
const route = useRoute()
const slug = computed(() => {
  const parts = route.params.slug
  return Array.isArray(parts) ? parts.join('/') : String(parts || '')
})

const { data: page } = await useAsyncData(
  () => 'wiki-' + route.path,
    () => $fetch(`/api/wiki/${slug.value.split('/').map(encodeURIComponent).join('/')}`).catch(() => null),
)

const { data: catalog } = await useAsyncData('wiki-catalog', () => $fetch('/api/wiki'))

const categoryName = computed(() => {
  const raw = slug.value
  if (raw.startsWith('Category:')) return raw.slice('Category:'.length).replace(/_/g, ' ')
  if (raw.startsWith('Category/')) return raw.slice('Category/'.length).replace(/_/g, ' ')
  return ''
})

const members = computed(() => {
  if (!categoryName.value || !catalog.value) return []
  const want = categoryName.value.toLowerCase()
  return catalog.value.filter((item) =>
    (item.categories || []).some((c) => c.toLowerCase() === want),
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
        <NuxtLink :to="'/wiki/Category:' + cat.replace(/ /g, '_')">{{ cat }}</NuxtLink>
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
