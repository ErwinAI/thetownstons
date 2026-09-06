<script setup lang="ts">
import { wikiHref } from '#shared/wiki'

const { isAdmin } = useWikiAccess()
const { ready } = useAuth()
const route = useRoute()

if (import.meta.client) {
  watch([ready, isAdmin], () => {
    if (ready.value && !isAdmin.value) navigateTo('/')
  }, { immediate: true })
}
const userFilter = computed(() => String(route.query.user || '').trim())

const { data } = await useAsyncData(
  () => 'changes-' + userFilter.value,
  () => $fetch('/api/changes', { query: userFilter.value ? { user: userFilter.value } : {} }),
)

const list = computed(() => Array.isArray(data.value) ? data.value : [])

function when(iso: string) {
  try {
    return new Date(iso).toLocaleString()
  }
  catch {
    return iso
  }
}

useHead({ title: userFilter.value ? `Changes by ${userFilter.value}` : 'Recent changes' })
</script>

<template>
  <article>
    <h1 class="firstHeading">{{ userFilter ? `Changes by ${userFilter}` : 'Recent changes' }}</h1>
    <div id="siteSub">From Townstons</div>
    <p v-if="userFilter"><NuxtLink to="/changes">All changes</NuxtLink></p>
    <p v-if="!list.length">No edits yet.</p>
    <table v-else class="wiki-history">
      <thead>
        <tr>
          <th>When</th>
          <th>Page</th>
          <th>User</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in list" :key="row.id">
          <td>{{ when(row.created_at) }}</td>
          <td><NuxtLink :to="wikiHref(row.path)">{{ row.title }}</NuxtLink></td>
          <td>
            <NuxtLink v-if="row.editor && row.editor !== 'recovered' && row.editor !== '—'" :to="'/changes?user=' + encodeURIComponent(row.editor)">{{ row.editor }}</NuxtLink>
            <template v-else>{{ row.editor }}</template>
          </td>
        </tr>
      </tbody>
    </table>
  </article>
</template>
