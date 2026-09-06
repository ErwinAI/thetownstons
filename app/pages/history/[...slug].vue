<script setup lang="ts">
import { sanitizeWikiHtml, wikiHref } from '#shared/wiki'

const route = useRoute()
const { user, token } = useAuth()
const { isAdmin } = useWikiAccess()

const slug = computed(() => {
  const parts = route.params.slug
  const raw = Array.isArray(parts) ? parts.join('/') : String(parts || '')
  try {
    return decodeURIComponent(raw)
  }
  catch {
    return raw
  }
})

const { data, refresh } = await useAsyncData(
  () => 'history-' + slug.value,
  () => $fetch('/api/history/' + slug.value),
)

const viewingId = ref<number | null>(null)
const diffingId = ref<number | null>(null)
const { data: viewed } = await useAsyncData(
  () => 'rev-' + slug.value + '-' + viewingId.value,
  () => viewingId.value
    ? $fetch('/api/history/' + slug.value, { query: { id: viewingId.value } })
    : Promise.resolve(null),
  { watch: [viewingId] },
)
const { data: diffed } = await useAsyncData(
  () => 'diff-' + slug.value + '-' + diffingId.value,
  () => diffingId.value
    ? $fetch('/api/history/' + slug.value, { query: { id: diffingId.value, diff: 1 } })
    : Promise.resolve(null),
  { watch: [diffingId] },
)

const error = ref('')
const pending = ref(false)

const page = computed(() => data.value?.page)
const revisions = computed(() => data.value?.revisions || [])
const viewTo = computed(() => wikiHref(page.value?.path || '/wiki/' + slug.value))
const editTo = computed(() => '/edit/' + slug.value)
const previewHtml = computed(() => sanitizeWikiHtml(viewed.value?.revision?.html || ''))

function when(iso: string) {
  try {
    return new Date(iso).toLocaleString()
  }
  catch {
    return iso
  }
}

async function revert(id: number) {
  error.value = ''
  pending.value = true
  try {
    const access = await token()
    if (!access) {
      await navigateTo('/login')
      return
    }
    await $fetch('/api/history/' + slug.value, {
      method: 'POST',
      headers: { Authorization: `Bearer ${access}` },
      body: { id },
    })
    await refresh()
    viewingId.value = id
    await navigateTo(viewTo.value)
  }
  catch (err) {
    const fetchErr = err as { data?: { statusMessage?: string }, message?: string }
    error.value = fetchErr.data?.statusMessage || fetchErr.message || 'Revert failed'
  }
  finally {
    pending.value = false
  }
}

useHead({ title: 'History of ' + (page.value?.title || slug.value) })
</script>

<template>
  <article>
    <WikiTitleBar :title="'Revision history of ' + (page?.title || slug)" :view-to="viewTo" :edit-to="editTo" />
    <div id="siteSub">From Townstons</div>
    <p v-if="!revisions.length">No saved revisions yet. The recovered page is the current text until someone edits it. The first save keeps that recovered copy here.</p>
    <p v-if="error" class="wiki-form-error">{{ error }}</p>
    <table v-if="revisions.length" class="wiki-history">
      <thead>
        <tr>
          <th>When</th>
          <th>Editor</th>
          <th>Title</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="rev in revisions" :key="rev.id">
          <td>{{ when(rev.created_at) }}</td>
          <td>{{ rev.editor || '—' }}</td>
          <td>{{ rev.title }}</td>
          <td>
            <button type="button" :class="{ 'is-on': viewingId === rev.id }" @click="viewingId = rev.id; diffingId = null">View</button>
            <button v-if="isAdmin" type="button" :class="{ 'is-on': diffingId === rev.id }" @click="diffingId = rev.id; viewingId = null">Diff</button>
            <button v-if="isAdmin" type="button" :disabled="pending" @click="revert(rev.id)">Revert</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="isAdmin && revisions.length" class="wiki-edit-help">Diff is against the previous save. Revert writes that version back as the live page and adds a new history row.</p>
    <div v-if="diffed?.lines" class="wiki-diff">
      <h2>Diff of {{ diffed.revision?.title }}</h2>
      <p class="wiki-edit-help">{{ when(diffed.revision?.created_at) }} · {{ diffed.revision?.editor || '—' }}</p>
      <pre class="wiki-diff-body"><span v-for="(line, i) in diffed.lines" :key="i" :class="'wiki-diff-' + line.type">{{ line.type === 'add' ? '+' : line.type === 'del' ? '-' : ' ' }}{{ line.text }}</span></pre>
    </div>
    <div v-if="viewed?.revision" class="wiki-body">
      <h2>{{ viewed.revision.title }}</h2>
      <p class="wiki-edit-help">{{ when(viewed.revision.created_at) }} · {{ viewed.revision.editor || '—' }}</p>
      <div v-html="previewHtml" />
    </div>
  </article>
</template>
