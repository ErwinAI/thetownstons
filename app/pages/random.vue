<script setup lang="ts">
const { data: pages } = await useAsyncData('wiki-random-list', () => $fetch('/api/wiki'))

onMounted(() => {
  if (!pages.value?.length) {
    navigateTo('/all', { replace: true })
    return
  }
  const i = Math.floor(Math.random() * pages.value.length)
  navigateTo(pages.value[i]!.path, { replace: true })
})

useHead({ title: 'Random page' })
</script>

<template>
  <p>Finding a random page…</p>
</template>
