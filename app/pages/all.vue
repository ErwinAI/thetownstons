<script setup lang="ts">
const { data: pages } = await useAsyncData('wiki-all', () => $fetch('/api/pages').catch(() => []))
const list = computed(() => Array.isArray(pages.value) ? pages.value : [])

useHead({ title: 'All pages' })
</script>

<template>
  <div>
    <h1 class="firstHeading">All pages</h1>
    <div id="siteSub">From Townstons</div>
    <p>{{ list.length }} recovered articles.</p>
    <div class="article-list">
      <NuxtLink v-for="page in list" :key="page.path" :to="page.path">
        {{ page.title }}
      </NuxtLink>
    </div>
  </div>
</template>
