<script setup lang="ts">
const { data: pages } = await useAsyncData('wiki-all', () => $fetch('/api/wiki'))

useHead({ title: 'All pages' })
</script>

<template>
  <div>
    <h1 class="firstHeading">All pages</h1>
    <div id="siteSub">From Townstons</div>
    <p>{{ pages?.length ?? 0 }} recovered articles.</p>
    <div class="article-list">
      <NuxtLink v-for="page in pages" :key="page.path" :to="page.path">
        {{ page.title }}
      </NuxtLink>
    </div>
  </div>
</template>
