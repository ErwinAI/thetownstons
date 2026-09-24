<script setup lang="ts">
import '~/assets/css/fit.css'
import { isFitHost, WIKI_ORIGIN } from '#shared/fit'

const FIT_TITLE = 'Dungeon Runners Character Fit Viewer (patent pending)'
const FIT_DESC = 'Look up a Dungeon Runners character: gear, skill tray, and spent attributes.'

const url = useRequestURL()
const fitHost = computed(() => isFitHost(url.host))
const home = computed(() => (fitHost.value ? '/' : '/fit'))
const searchesHref = computed(() => (fitHost.value ? '/searches' : '/fit/searches'))
const origin = computed(() => `${url.protocol}//${url.host}`)
const homeAbs = computed(() => origin.value + (fitHost.value ? '/' : '/fit'))
const defaultOg = computed(() => `${origin.value}/fit/og-default.png`)

useHead({
  title: FIT_TITLE,
  titleTemplate: (title?: string) => {
    if (!title || title === FIT_TITLE) return FIT_TITLE
    return `${title} · Fit`
  },
  htmlAttrs: { lang: 'en' },
  link: [
    { rel: 'icon', href: '/favicon.ico', sizes: '32x32' },
    { rel: 'icon', type: 'image/png', href: '/favicon.png', sizes: '32x32' },
    { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' },
  ],
})

useSeoMeta({
  description: FIT_DESC,
  ogType: 'website',
  ogSiteName: 'Fit',
  ogTitle: FIT_TITLE,
  ogDescription: FIT_DESC,
  ogUrl: homeAbs,
  ogImage: defaultOg,
  ogImageWidth: 1200,
  ogImageHeight: 630,
  ogImageAlt: FIT_TITLE,
  ogImageType: 'image/png',
  twitterCard: 'summary_large_image',
  twitterTitle: FIT_TITLE,
  twitterDescription: FIT_DESC,
  twitterImage: defaultOg,
  themeColor: '#140a05',
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
      <nav class="fit-midnav">
        <NuxtLink class="fit-last-searched" :to="searchesHref">Last searched</NuxtLink>
      </nav>
      <div class="fit-search-row">
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
