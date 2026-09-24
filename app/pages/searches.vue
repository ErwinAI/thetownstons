<script setup lang="ts">
import { isFitHost } from '#shared/fit'

const url = useRequestURL()
if (!isFitHost(url.host)) {
  throw createError({ statusCode: 404, statusMessage: 'Page not found' })
}
</script>

<template>
  <FitSearches />
</template>
