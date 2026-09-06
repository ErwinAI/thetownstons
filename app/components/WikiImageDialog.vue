<script setup lang="ts">
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ insert: [snippet: string] }>()

const { token } = useAuth()
const file = ref<File | null>(null)
const caption = ref('')
const align = ref('right')
const error = ref('')
const busy = ref(false)

function onFile(ev: Event) {
  const input = ev.target as HTMLInputElement
  file.value = input.files?.[0] || null
}

async function upload() {
  error.value = ''
  if (!file.value) {
    error.value = 'Choose an image'
    return
  }
  busy.value = true
  try {
    const access = await token()
    if (!access) {
      error.value = 'Log in first'
      return
    }
    const form = new FormData()
    form.append('file', file.value)
    const row = await $fetch<{ id: string, src: string }>('/api/uploads', {
      method: 'POST',
      headers: { Authorization: `Bearer ${access}` },
      body: form,
    })
    const cap = caption.value.trim()
    const snippet = `{{thumb|src=${row.src}|caption=${cap}|align=${align.value}}}`
    emit('insert', snippet)
    caption.value = ''
    file.value = null
    open.value = false
  }
  catch (err) {
    const fetchErr = err as { data?: { statusMessage?: string }, message?: string }
    error.value = fetchErr.data?.statusMessage || fetchErr.message || 'Upload failed'
  }
  finally {
    busy.value = false
  }
}

function close() {
  if (!busy.value) open.value = false
}
</script>

<template>
  <div v-if="open" class="wiki-dialog-back" @click.self="close">
    <div class="wiki-dialog" role="dialog" aria-label="Upload image">
      <h2>Upload image</h2>
      <p class="wiki-edit-help">It shows as “To be approved” until an admin signs off. Jpeg, png, gif, or webp. 2 MB max.</p>
      <p><label>File<br><input type="file" accept="image/jpeg,image/png,image/gif,image/webp" @change="onFile"></label></p>
      <p><label>Caption<br><input v-model="caption"></label></p>
      <p>
        <label>Align
          <select v-model="align">
            <option value="right">Right</option>
            <option value="left">Left</option>
          </select>
        </label>
      </p>
      <p v-if="error" class="wiki-form-error">{{ error }}</p>
      <p>
        <button type="button" :disabled="busy" @click="upload">{{ busy ? 'Uploading…' : 'Upload and insert' }}</button>
        <button type="button" :disabled="busy" @click="close">Cancel</button>
      </p>
    </div>
  </div>
</template>
