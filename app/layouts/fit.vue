<script setup lang="ts">
import '~/assets/css/fit.css'
import { isFitHost, WIKI_ORIGIN } from '#shared/fit'

const url = useRequestURL()
const fitHost = computed(() => isFitHost(url.host))
const home = computed(() => (fitHost.value ? '/' : '/fit'))

useHead({
  titleTemplate: '%s · Fit',
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
      <NuxtLink :to="home" class="fit-brand">
        <img class="fit-logo" src="/fit/ui/logo.png" alt="Dungeon Runners" width="200" height="66">
        <span class="fit-brand-text">
          <strong>Fit</strong>
          <span>Townstons character viewer</span>
        </span>
      </NuxtLink>
      <form class="fit-search" @submit.prevent="go">
        <input v-model="q" type="search" name="name" placeholder="Character name" maxlength="64" aria-label="Character name">
        <button type="submit">Look up</button>
      </form>
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
