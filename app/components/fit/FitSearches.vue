<script setup lang="ts">
import { isFitHost } from '#shared/fit'
import { formatWhen } from '#shared/fit-xp'

type SearchRow = {
  name: string
  count?: number
  at?: string | null
}

const url = useRequestURL()
const fitHost = isFitHost(url.host)

useHead({
  title: 'Last searched',
  link: [{ rel: 'canonical', href: `${url.protocol}//${url.host}${fitHost ? '/searches' : '/fit/searches'}` }],
})

function hrefFor(name: string) {
  const slug = encodeURIComponent(name)
  return fitHost ? `/${slug}` : `/fit/${slug}`
}

const { data, error } = await useAsyncData('fit-searches', () =>
  $fetch<{ top: SearchRow[], recent: SearchRow[] }>('/api/fit/searches').catch(() => null),
)

const top = computed(() => data.value?.top || [])
const recent = computed(() => data.value?.recent || [])
</script>

<template>
  <div class="fit-home">
    <div class="fit-hero">
      <h1>Last searched</h1>
      <p>Names people actually typed in, not the daily board crawl.</p>
    </div>
    <p v-if="error" class="fit-status">Could not load searches.</p>
    <div v-else class="fit-boards">
      <section class="fit-board">
        <h2>Most searched</h2>
        <ol v-if="top.length">
          <li v-for="row in top" :key="'top-' + row.name">
            <NuxtLink :to="hrefFor(row.name)">{{ row.name }}</NuxtLink>
            <span> · {{ row.count }} {{ row.count === 1 ? 'lookup' : 'lookups' }}</span>
          </li>
        </ol>
        <p v-else class="fit-status">Nobody has looked anyone up yet.</p>
      </section>
      <section class="fit-board">
        <h2>Last 10</h2>
        <ol v-if="recent.length">
          <li v-for="row in recent" :key="'recent-' + row.name + (row.at || '')">
            <NuxtLink :to="hrefFor(row.name)">{{ row.name }}</NuxtLink>
            <span v-if="row.at"> · {{ formatWhen(row.at) }}</span>
          </li>
        </ol>
        <p v-else class="fit-status">Nothing here yet.</p>
      </section>
    </div>
  </div>
</template>
