<script setup lang="ts">
import { isFitHost } from '#shared/fit'

const props = defineProps<{ error: { statusCode?: number, statusMessage?: string } }>()
const url = useRequestURL()
const fit = computed(() => isFitHost(url.host) || url.pathname.startsWith('/fit'))
</script>

<template>
  <NuxtLayout :name="fit ? 'fit' : 'default'">
    <template v-if="fit">
      <p class="fit-error">
        {{ props.error?.statusCode === 404 ? 'Nobody public by that name.' : (props.error?.statusMessage || 'Something broke.') }}
      </p>
    </template>
    <template v-else>
      <h1 class="firstHeading">{{ props.error?.statusCode || 404 }}</h1>
      <div id="siteSub">From Townstons</div>
      <p>{{ props.error?.statusMessage || 'This page was not recovered from the archive.' }}</p>
      <p>
        Try the <NuxtLink to="/">Main Page</NuxtLink>
        or <NuxtLink to="/all">all recovered articles</NuxtLink>.
      </p>
    </template>
  </NuxtLayout>
</template>
