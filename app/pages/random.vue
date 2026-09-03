<script setup lang="ts">
const { data: pages } = await useAsyncData('wiki-random-list', () => $fetch('/api/pages').catch(() => []))

onMounted(() => {
  const list = Array.isArray(pages.value) ? pages.value : []
  if (!list.length) {
    navigateTo('/all', { replace: true })
    return
  }
  const i = Math.floor(Math.random() * list.length)
  navigateTo(list[i]!.path, { replace: true })
})

useHead({ title: 'Random page' })
</script>

<template>
  <p>Finding a random page…</p>
</template>
