<script setup lang="ts">
const { data } = await useAsyncData('wiki-random', () => $fetch('/api/random'))
if (data.value?.path) {
  await navigateTo(data.value.path, { replace: true })
}
else {
  await navigateTo('/all', { replace: true })
}
</script>

<template>
  <p>Finding a random page…</p>
</template>
