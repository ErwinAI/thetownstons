<script setup lang="ts">
import { isFitHost } from '#shared/fit'

const route = useRoute()
const url = useRequestURL()
const layout = computed(() => {
  if (isFitHost(url.host) || route.path === '/fit' || route.path.startsWith('/fit/')) return 'fit'
  return 'default'
})
</script>

<template>
  <NuxtLayout :name="layout">
    <NuxtPage />
  </NuxtLayout>
</template>
