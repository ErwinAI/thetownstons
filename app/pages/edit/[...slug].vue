<script setup lang="ts">
import { htmlToWikiMarkdown } from '#shared/html-to-md'
import { renderWikiMarkdown } from '#shared/wiki-md'
import { wikiApiPath, wikiHref } from '#shared/wiki'

const route = useRoute()
const { user, ready, token } = useAuth()
const { canEdit } = useWikiAccess()
const showUpload = ref(false)

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

if (import.meta.client) {
  watch([ready, user], () => {
    if (ready.value && !user.value) navigateTo('/login')
    else if (ready.value && !canEdit.value) navigateTo('/')
  }, { immediate: true })
}

const { data: page } = await useAsyncData(
  () => 'edit-' + slug.value,
  () => $fetch(wikiApiPath('/wiki/' + slug.value)).catch(() => null),
)

const title = ref(page.value?.title || slug.value.replace(/_/g, ' '))
const bodyMd = ref(initialSource(page.value))

function initialSource(current: { body_md?: string | null, html?: string } | null | undefined) {
  const stored = current?.body_md || ''
  const looksHtml = /^\s*</.test(stored) && /<(table|div|p|h[1-6]|ul)\b/i.test(stored)
  if (stored && !looksHtml) return stored
  const html = current?.html || stored
  return html ? htmlToWikiMarkdown(html) : ''
}
const categoriesText = ref((page.value?.categories || []).join('\n'))
const error = ref('')
const pending = ref(false)
const isCategory = computed(() => /^Category[/:]/i.test(slug.value))

function categoriesFromField() {
  return categoriesText.value.split(/[\n,]+/).map((item) => item.replace(/^Category:/i, '').trim()).filter(Boolean)
}

const preview = computed(() => renderWikiMarkdown(bodyMd.value))
const viewTo = computed(() => wikiHref('/wiki/' + (page.value?.path?.replace(/^\/wiki\//, '') || slug.value)))
const historyTo = computed(() => '/history/' + slug.value)
const helpQuest = '{{quest|giver=|type=|reward=|repeatable=}}'
const helpThumb = '{{thumb|src=/images/x.jpg|caption=|align=right}}'
const helpBox = '{{infobox|piece=Helm|class=Fighter}}'

async function save() {
  error.value = ''
  pending.value = true
  try {
    const access = await token()
    if (!access) {
      await navigateTo('/login')
      return
    }
    await $fetch(wikiApiPath('/wiki/' + slug.value), {
      method: 'PUT',
      headers: { Authorization: `Bearer ${access}` },
      body: { title: title.value, body_md: bodyMd.value, categories: categoriesFromField() },
    })
    await navigateTo(viewTo.value)
  }
  catch (err) {
    const fetchErr = err as { data?: { statusMessage?: string }, message?: string }
    error.value = fetchErr.data?.statusMessage || fetchErr.message || 'Save failed'
  }
  finally {
    pending.value = false
  }
}

function insertImage(snippet: string) {
  bodyMd.value = (bodyMd.value ? bodyMd.value.trimEnd() + '\n\n' : '') + snippet + '\n'
}

useHead({ title: 'Edit ' + title.value })
</script>

<template>
  <article>
    <WikiTitleBar :title="'Editing ' + title" :view-to="viewTo" :history-to="historyTo" />
    <div id="siteSub">From Townstons</div>
    <p class="wiki-edit-help">
      Markdown plus templates:
      <code>{{ helpQuest }}</code>,
      <code>{{ helpThumb }}</code>,
      <code>{{ helpBox }}</code>.
      Recovered HTML is converted the first time you open this editor.
      Member lists on category pages are automatic — do not paste article links into the source.
    </p>
    <form class="wiki-form" @submit.prevent="save">
      <p><label>Title<br><input v-model="title" required></label></p>
      <p><label>Source<br><textarea v-model="bodyMd" class="wiki-md" spellcheck="true" /></label></p>
      <p><button type="button" @click="showUpload = true">Add image</button></p>
      <WikiImageDialog v-model:open="showUpload" @insert="insertImage" />
      <p v-if="error" class="wiki-form-error">{{ error }}</p>
      <h2>Preview</h2>
      <div class="wiki-body" v-html="preview" />
      <p>
        <label>{{ isCategory ? 'Parent categories' : 'Categories' }}<br>
          <textarea v-model="categoriesText" class="wiki-cats" rows="4" />
        </label>
        <span class="wiki-edit-help">One per line. {{ isCategory ? 'This category page will show up under those parents.' : 'This page will appear on those category pages. No need to edit the category article.' }}</span>
      </p>
      <p><button type="submit" :disabled="pending">{{ pending ? 'Saving…' : 'Save' }}</button></p>
    </form>
  </article>
</template>
