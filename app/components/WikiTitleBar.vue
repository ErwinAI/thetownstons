<script setup lang="ts">
const props = defineProps<{
  title: string
  historyTo?: string
  editTo?: string
  viewTo?: string
}>()
const { canEdit } = useWikiAccess()
</script>

<template>
  <div class="wiki-title-row">
    <h1 class="firstHeading">{{ props.title }}</h1>
    <nav class="wiki-title-tools">
      <NuxtLink v-if="viewTo" :to="viewTo">View</NuxtLink>
      <NuxtLink v-if="historyTo" :to="historyTo">History</NuxtLink>
      <NuxtLink v-if="canEdit && editTo" :to="editTo">Edit</NuxtLink>
    </nav>
  </div>
</template>
