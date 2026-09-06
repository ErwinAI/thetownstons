<script setup lang="ts">
const route = useRoute()
const q = computed(() => String(route.query.q || '').trim())
const typed = ref(q.value)

watch(q, (value) => {
  typed.value = value
})

const { data: hits } = await useAsyncData(
  () => 'search-' + q.value,
  () => q.value.length >= 2
    ? $fetch('/api/search', { query: { q: q.value } }).catch(() => [])
    : Promise.resolve([]),
)

const list = computed(() => Array.isArray(hits.value) ? hits.value : [])

useHead({ title: q.value ? `Search: ${q.value}` : 'Search' })

function go() {
  const next = typed.value.trim()
  navigateTo(next ? { path: '/search', query: { q: next } } : '/search')
}
</script>

<template>
  <div>
    <h1 class="firstHeading">Search</h1>
    <div id="siteSub">From Townstons</div>

    <form class="wiki-form wiki-search-form" @submit.prevent="go">
      <p>
        <label>Search the wiki<br>
          <input v-model="typed" type="search" name="q" autofocus>
        </label>
      </p>
      <p><button type="submit">Search</button></p>
    </form>

    <p v-if="q && q.length < 2">Type at least two letters.</p>
    <p v-else-if="q && !list.length">No pages matched <b>{{ q }}</b>.</p>
    <p v-else-if="q">{{ list.length }} page{{ list.length === 1 ? '' : 's' }} for <b>{{ q }}</b>.</p>

    <ul v-if="list.length" class="wiki-search-hits">
      <li v-for="hit in list" :key="hit.path">
        <NuxtLink :to="hit.path">{{ hit.title }}</NuxtLink>
        <p v-if="hit.headline" class="wiki-search-snippet" v-html="hit.headline"></p>
      </li>
    </ul>
  </div>
</template>
