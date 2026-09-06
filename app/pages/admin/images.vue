<script setup lang="ts">
const { isAdmin } = useWikiAccess()
const { ready, token } = useAuth()
const list = ref<{ id: string, src: string, original_name?: string, username?: string, created_at: string }[]>([])
const error = ref('')

async function load() {
  const access = await token()
  if (!access) return
  list.value = await $fetch('/api/uploads', { headers: { Authorization: `Bearer ${access}` } }).catch(() => [])
}

if (import.meta.client) {
  watch([ready, isAdmin], () => {
    if (ready.value && !isAdmin.value) navigateTo('/')
    if (ready.value && isAdmin.value) load()
  }, { immediate: true })
}

async function act(id: string, action: 'approve' | 'reject') {
  error.value = ''
  const access = await token()
  if (!access) return
  try {
    await $fetch(`/api/uploads/${id}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${access}` },
      body: { action },
    })
    await load()
  }
  catch (err) {
    const fetchErr = err as { data?: { statusMessage?: string }, message?: string }
    error.value = fetchErr.data?.statusMessage || fetchErr.message || 'Failed'
  }
}

function when(iso: string) {
  try {
    return new Date(iso).toLocaleString()
  }
  catch {
    return iso
  }
}

useHead({ title: 'Approve images' })
</script>

<template>
  <article>
    <h1 class="firstHeading">Approve images</h1>
    <div id="siteSub">From Townstons</div>
    <p v-if="error" class="wiki-form-error">{{ error }}</p>
    <p v-if="!list.length">Nothing waiting.</p>
    <table v-else class="wiki-history">
      <thead>
        <tr>
          <th>Image</th>
          <th>User</th>
          <th>When</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in list" :key="row.id">
          <td>
            <img :src="row.src" alt="" class="wiki-admin-thumb">
            <div class="wiki-edit-help">{{ row.original_name }}</div>
          </td>
          <td>{{ row.username }}</td>
          <td>{{ when(row.created_at) }}</td>
          <td>
            <button type="button" @click="act(row.id, 'approve')">Approve</button>
            <button type="button" @click="act(row.id, 'reject')">Reject</button>
          </td>
        </tr>
      </tbody>
    </table>
  </article>
</template>
