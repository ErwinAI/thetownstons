<script setup lang="ts">
const props = defineProps<{ error: { statusCode?: number, statusMessage?: string } }>()
</script>

<template>
  <NuxtLayout>
    <h1 class="firstHeading">{{ props.error?.statusCode || 404 }}</h1>
    <div id="siteSub">From Townstons</div>
    <p>{{ props.error?.statusMessage || 'This page was not recovered from the archive.' }}</p>
    <p>
      Try the <NuxtLink to="/">Main Page</NuxtLink>
      or <NuxtLink to="/all">all recovered articles</NuxtLink>.
    </p>
  </NuxtLayout>
</template>
