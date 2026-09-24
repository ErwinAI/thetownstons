<script setup lang="ts">
import '~/assets/css/fit.css'
import { isFitHost, WIKI_ORIGIN } from '#shared/fit'

const FIT_TITLE = 'Dungeon Runners Character Fit Viewer (patent pending)'

const url = useRequestURL()
const fitHost = computed(() => isFitHost(url.host))
const home = computed(() => (fitHost.value ? '/' : '/fit'))
const searchesHref = computed(() => (fitHost.value ? '/searches' : '/fit/searches'))

useHead({
  title: FIT_TITLE,
  titleTemplate: (title?: string) => {
    if (!title || title === FIT_TITLE) return FIT_TITLE
    return `${title} · Fit`
  },
  meta: [
    { name: 'description', content: 'Look up a Dungeon Runners character: gear, skill tray, and spent attributes.' },
  ],
})

const q = ref('')

function go() {
  const name = q.value.replace(/\s+/g, ' ').trim()
  if (!name) return
  const slug = encodeURIComponent(name)
  return navigateTo(fitHost.value ? `/${slug}` : `/fit/${slug}`)
}
</script>

<template>
  <div class="fit-app">
    <header class="fit-top">
      <div class="fit-brand">
        <NuxtLink :to="home" class="fit-brand-home">
          <img class="fit-logo" src="/wiki-logo.png" alt="The Townstons" width="48" height="48">
          <strong>{{ FIT_TITLE }}</strong>
        </NuxtLink>
        <a class="fit-by" :href="WIKI_ORIGIN">by the townstons</a>
      </div>
      <div class="fit-search-row">
        <NuxtLink class="fit-last-searched" :to="searchesHref">Last searched</NuxtLink>
        <form class="fit-search" @submit.prevent="go">
          <input v-model="q" type="search" name="name" placeholder="Character name" maxlength="64" aria-label="Character name">
          <button type="submit">Look up</button>
        </form>
      </div>
    </header>
    <main class="fit-main">
      <slot />
    </main>
    <footer class="fit-foot">
      Public character data from Dungeon Runners Reborn.
      <a :href="WIKI_ORIGIN">The Townstons wiki</a>
    </footer>
  </div>
</template>
