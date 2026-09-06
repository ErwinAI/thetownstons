<script setup lang="ts">
import { titleToSlug } from '#shared/username'

const { user, ready } = useAuth()
const { canEdit } = useWikiAccess()
const title = ref('')

if (import.meta.client) {
  watch([ready, user, canEdit], () => {
    if (ready.value && !user.value) navigateTo('/login')
    else if (ready.value && !canEdit.value) navigateTo('/')
  }, { immediate: true })
}

function go() {
  const slug = titleToSlug(title.value)
  if (!slug) return
  navigateTo('/edit/' + slug)
}

useHead({ title: 'New page' })
</script>

<template>
  <article>
    <h1 class="firstHeading">New page</h1>
    <div id="siteSub">From Townstons</div>
    <p>Give it a title. You write the page on the next screen.</p>
    <form class="wiki-form" @submit.prevent="go">
      <p><label>Title<br><input v-model="title" required autofocus></label></p>
      <p><button type="submit">Create</button></p>
    </form>
  </article>
</template>
