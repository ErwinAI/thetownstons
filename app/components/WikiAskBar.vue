<script setup lang="ts">
const route = useRoute()
const karlPage = useKarlPage()
const { user, ready } = useAuth()
const { confirmed } = useWikiAccess()
const hide = computed(() => route.path === '/karl')

const pagePill = computed(() => {
  const page = karlPage.value
  if (!page?.title || !page.path) return null
  if (page.path === '/wiki/Main_Page' || page.path === '/') return null
  return page
})

async function openKarl() {
  if (!ready.value) return
  if (!user.value) {
    await navigateTo('/signup?from=karl')
    return
  }
  if (!confirmed.value) {
    await navigateTo('/login?from=karl')
    return
  }
  await navigateTo({
    path: '/karl',
    query: pagePill.value ? { page: pagePill.value.path } : {},
  })
}
</script>

<template>
  <div v-if="!hide" class="wiki-ask">
    <button type="button" class="wiki-ask-hud" @click="openKarl">
      <img class="wiki-ask-karl" src="/images/karl.png?v=2" width="64" height="85" alt="">
      <span class="wiki-ask-xp">Ask KarlAI</span>
    </button>
  </div>
</template>
