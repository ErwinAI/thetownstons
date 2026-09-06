<script setup lang="ts">
import { DefaultChatTransport } from 'ai'
import { useChat } from '@ai-sdk/vue'
import { marked } from 'marked'
import { sanitizeWikiHtml } from '#shared/wiki'
import type { KarlPageRef } from '~/composables/useKarlPage'

type SearchHit = { title: string, path: string }
type ComposeBit = { t: 'text', v: string } | { t: 'page', title: string, path: string }

const MENTION_MIN = 3
const AT_TAIL = /(^|[\s])@([^\s@]*)$/
const MENTION_TOKEN = /\[\[([^\]|]+)\|(\/wiki\/[^\]]+)\]\]/g

const route = useRoute()
const draft = ref('')
const bits = ref<ComposeBit[]>([])
const sendingMentions = ref<KarlPageRef[]>([])
const notice = ref('')
const suggest = ref<SearchHit[]>([])
const searching = ref(false)
const suggestOn = ref(false)
const thread = ref<HTMLElement | null>(null)
const karlPage = useKarlPage()
const { user, ready, token } = useAuth()
const { confirmed } = useWikiAccess()

const pageFromQuery = computed(() => {
  const raw = String(route.query.page || '')
  return raw.startsWith('/wiki/') ? raw : ''
})

const pagePill = computed(() => {
  if (pageFromQuery.value) {
    const title = decodeURIComponent(pageFromQuery.value.replace(/^\/wiki\//, '')).replace(/_/g, ' ')
    if (karlPage.value?.path === pageFromQuery.value) {
      return karlPage.value
    }
    return { title, path: pageFromQuery.value }
  }
  const page = karlPage.value
  if (!page?.title || !page.path) return null
  if (page.path === '/wiki/Main_Page' || page.path === '/') return null
  return page
})

const { messages, sendMessage, status, error } = useChat({
  transport: new DefaultChatTransport({
    api: '/api/chat',
    headers: async () => {
      const access = await token()
      return access ? { Authorization: `Bearer ${access}` } : {}
    },
    prepareSendMessagesRequest: ({ messages, id, body }) => ({
      body: {
        ...body,
        id,
        messages: stripOutgoing(messages),
        page: pagePill.value,
        mentions: sendingMentions.value,
      },
    }),
  }),
})

const busy = computed(() => status.value === 'submitted' || status.value === 'streaming' || status.value === 'generating')

const WAIT_LINES = [
  'Ugh. Thinking. Hurts my brain.',
  'Hold the sign. Karl is counting on his fingers.',
  'I used to just hold a number. Now I have to read. Tragic.',
  'Give me a second, Dungeon Runner. Too many words.',
  'Looking. Still looking. Do not stare.',
  'The sign is heavy. The question is worse.',
  'Karlbucks first. Then I remember how your pants work.',
  'If this takes longer I am charging Karl Points.',
]

const waitLine = ref(WAIT_LINES[0])
let waitTimer: ReturnType<typeof setInterval> | null = null

watch(busy, (on) => {
  if (waitTimer) {
    clearInterval(waitTimer)
    waitTimer = null
  }
  if (!on) return
  let i = Math.floor(Math.random() * WAIT_LINES.length)
  waitLine.value = WAIT_LINES[i]
  waitTimer = setInterval(() => {
    i = (i + 1) % WAIT_LINES.length
    waitLine.value = WAIT_LINES[i]
  }, 2600)
}, { immediate: true })

onUnmounted(() => {
  if (waitTimer) clearInterval(waitTimer)
})

const mentionNeedle = computed(() => {
  const match = draft.value.match(AT_TAIL)
  return match ? match[2] : null
})

const suggestHint = computed(() => {
  if (mentionNeedle.value == null) return ''
  if (mentionNeedle.value.length < MENTION_MIN) return 'Continue typing to search'
  if (searching.value) return 'Searching.'
  if (!suggest.value.length) return 'No pages.'
  return ''
})

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(mentionNeedle, (needle) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (needle == null) {
    suggest.value = []
    suggestOn.value = false
    searching.value = false
    return
  }
  suggestOn.value = true
  if (needle.length < MENTION_MIN) {
    suggest.value = []
    searching.value = false
    return
  }
  searching.value = true
  suggest.value = []
  searchTimer = setTimeout(async () => {
    const hits = await $fetch<SearchHit[]>('/api/search', { query: { q: needle } }).catch(() => [])
    if (mentionNeedle.value !== needle) return
    suggest.value = (Array.isArray(hits) ? hits : []).slice(0, 8)
    searching.value = false
  }, 180)
})

watch([messages, waitLine], async () => {
  await nextTick()
  if (thread.value) thread.value.scrollTop = thread.value.scrollHeight
}, { deep: true })

function mentionsFromBits(): KarlPageRef[] {
  const out: KarlPageRef[] = []
  for (const bit of bits.value) {
    if (bit.t === 'page' && !out.some((row) => row.path === bit.path)) {
      out.push({ title: bit.title, path: bit.path })
    }
  }
  return out.slice(0, 5)
}

function serializeCompose() {
  let text = ''
  for (const bit of bits.value) {
    text += bit.t === 'page' ? `[[${bit.title}|${bit.path}]]` : bit.v
  }
  return text + draft.value
}

function stripMentionTokens(text: string) {
  return text.replace(MENTION_TOKEN, '$1')
}

function stripOutgoing(messages: { parts?: { type: string, text?: string }[] }[]) {
  return messages.map((message) => ({
    ...message,
    parts: (message.parts || []).map((part) => (
      part.type === 'text' && 'text' in part
        ? { ...part, text: stripMentionTokens(String(part.text || '')) }
        : part
    )),
  }))
}

function addMention(hit: SearchHit) {
  const match = draft.value.match(AT_TAIL)
  if (!match || match.index == null) return
  const before = draft.value.slice(0, match.index) + match[1]
  const next = [...bits.value]
  if (before) next.push({ t: 'text', v: before })
  if (pagePill.value?.path !== hit.path && !next.some((bit) => bit.t === 'page' && bit.path === hit.path)) {
    if (mentionsFromBits().length >= 5) {
      draft.value = before
      suggestOn.value = false
      return
    }
    next.push({ t: 'page', title: hit.title, path: hit.path })
  }
  bits.value = next
  draft.value = ''
  suggest.value = []
  suggestOn.value = false
  searching.value = false
}

function dropMention(index: number) {
  bits.value = bits.value.filter((_, i) => i !== index)
}

function partText(part: { type: string, text?: string }) {
  return part.type === 'text' ? String(part.text || '') : ''
}

function hasText(message: { parts?: { type: string, text?: string }[] }) {
  return (message.parts || []).some((part) => Boolean(partText(part)))
}

const waitingOnKarl = computed(() => {
  if (!busy.value) return false
  const last = messages.value[messages.value.length - 1]
  return !last || last.role === 'user' || !hasText(last)
})

function messageTexts(message: { parts?: { type: string, text?: string }[] }) {
  return (message.parts || []).map((part) => partText(part)).filter(Boolean)
}

function karlHtml(text: string): string {
  const raw = String(marked.parse(text, { async: false, gfm: true, breaks: true }))
  return sanitizeWikiHtml(
    raw
      .replace(/<script[\s\S]*?<\/script>/gi, '')
      .replace(/<style[\s\S]*?<\/style>/gi, '')
      .replace(/<\/?(?:iframe|object|embed|link|meta)[^>]*>/gi, '')
      .replace(/\son[a-z]+="[^"]*"/gi, '')
      .replace(/\son[a-z]+='[^']*'/gi, '')
      .replace(/href="javascript:[^"]*"/gi, 'href="#"'),
  )
}

function messageHtml(message: { parts?: { type: string, text?: string }[] }) {
  return messageTexts(message).map(karlHtml).join('')
}

function userSegs(text: string): ComposeBit[] {
  const out: ComposeBit[] = []
  const re = /\[\[([^\]|]+)\|(\/wiki\/[^\]]+)\]\]/g
  let last = 0
  for (const match of text.matchAll(re)) {
    const at = match.index || 0
    if (at > last) out.push({ t: 'text', v: text.slice(last, at) })
    out.push({ t: 'page', title: match[1], path: match[2] })
    last = at + match[0].length
  }
  if (last < text.length) out.push({ t: 'text', v: text.slice(last) })
  return out
}

onMounted(async () => {
  if (!ready.value) return
  if (!user.value) {
    await navigateTo('/signup?from=karl')
    return
  }
  if (!confirmed.value) {
    notice.value = 'Confirm your email first. Karl stays quiet until then.'
  }
})

async function submit() {
  if (suggestOn.value && suggest.value[0]) {
    addMention(suggest.value[0])
    return
  }
  const text = serializeCompose().trim()
  if (!text || !ready.value) return
  if (!user.value) {
    await navigateTo('/signup?from=karl')
    return
  }
  if (!confirmed.value) {
    notice.value = 'Confirm your email first. Karl stays quiet until then.'
    return
  }
  sendingMentions.value = mentionsFromBits()
  bits.value = []
  draft.value = ''
  suggest.value = []
  suggestOn.value = false
  searching.value = false
  await sendMessage({ text })
  sendingMentions.value = []
}

function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') suggestOn.value = false
  if (event.key === 'Backspace' && !draft.value && bits.value.length) {
    event.preventDefault()
    const last = bits.value[bits.value.length - 1]
    bits.value = bits.value.slice(0, -1)
    if (last.t === 'text') draft.value = last.v
    return
  }
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    submit()
  }
}

useHead({ title: 'KarlAI' })
</script>

<template>
  <article class="karl-page">
    <WikiTitleBar title="KarlAI" />
    <div id="siteSub">From The Townstons</div>

    <div ref="thread" class="karl-thread">
      <p v-if="notice" class="wiki-form-error">{{ notice }}</p>
      <p v-if="error" class="wiki-form-error">{{ error.message || 'Karl hit a wall.' }}</p>
      <p v-if="!messages.length && !notice" class="wiki-ask-empty">Ask about an item, quest, or how something works. Type @ to name a page.</p>
      <div
        v-for="message in messages"
        :key="message.id"
        class="wiki-ask-msg"
        :class="'is-' + message.role"
      >
        <div class="karl-who">
          <img
            v-if="message.role !== 'user'"
            class="karl-face"
            src="/images/karl.png?v=2"
            width="28"
            height="37"
            alt=""
          >
          <b>{{ message.role === 'user' ? 'You' : 'Karl' }}</b>
        </div>
        <template v-if="message.role === 'user'">
          <p v-for="(bit, idx) in messageTexts(message)" :key="'t' + idx" class="karl-user-line">
            <template v-for="(seg, sidx) in userSegs(bit)" :key="sidx">
              <span v-if="seg.t === 'page'" class="wiki-ask-pill is-mention">
                <svg class="karl-page-icon" viewBox="0 0 16 16" aria-hidden="true">
                  <path fill="currentColor" d="M4 1.5h6.2L13 4.8V14.5H4z" />
                  <path fill="none" stroke="currentColor" stroke-width="1.2" d="M10.2 1.5V4.8H13" />
                </svg>
                {{ seg.title }}
              </span>
              <template v-else>{{ seg.v }}</template>
            </template>
          </p>
        </template>
        <div v-else-if="hasText(message)" class="karl-md" v-html="messageHtml(message)" />
        <p
          v-if="busy && message.role !== 'user' && !hasText(message)"
          class="wiki-ask-status"
        >{{ waitLine }}</p>
      </div>
      <div v-if="waitingOnKarl && (!messages.length || messages[messages.length - 1].role === 'user')" class="wiki-ask-msg is-assistant">
        <div class="karl-who">
          <img class="karl-face" src="/images/karl.png?v=2" width="28" height="37" alt="">
          <b>Karl</b>
        </div>
        <p class="wiki-ask-status">{{ waitLine }}</p>
      </div>
    </div>

    <form class="karl-compose" @submit.prevent="submit">
      <div class="wiki-ask-field karl-field" :class="{ 'has-inline': bits.length || pagePill }">
        <span v-if="pagePill" class="wiki-ask-pill is-page">
          <svg class="karl-page-icon" viewBox="0 0 16 16" aria-hidden="true">
            <path fill="currentColor" d="M4 1.5h6.2L13 4.8V14.5H4z" />
            <path fill="none" stroke="currentColor" stroke-width="1.2" d="M10.2 1.5V4.8H13" />
          </svg>
          {{ pagePill.title }}
        </span>
        <template v-for="(bit, idx) in bits" :key="bit.t === 'page' ? bit.path + idx : 't' + idx">
          <span v-if="bit.t === 'text'" class="karl-inline-text">{{ bit.v }}</span>
          <button
            v-else
            type="button"
            class="wiki-ask-pill is-mention"
            @click="dropMention(idx)"
          >
            <svg class="karl-page-icon" viewBox="0 0 16 16" aria-hidden="true">
              <path fill="currentColor" d="M4 1.5h6.2L13 4.8V14.5H4z" />
              <path fill="none" stroke="currentColor" stroke-width="1.2" d="M10.2 1.5V4.8H13" />
            </svg>
            {{ bit.title }}
          </button>
        </template>
        <textarea
          v-model="draft"
          :rows="bits.length || pagePill ? 1 : 3"
          maxlength="1500"
          :placeholder="bits.length || pagePill ? '' : 'Ask KarlAI…'"
          aria-label="Ask KarlAI"
          :disabled="busy || !confirmed"
          @keydown="onKey"
        />
      </div>
      <button class="karl-ask-btn" type="submit" :disabled="busy || !confirmed">{{ busy ? '…' : 'Ask' }}</button>
      <ul v-if="suggestOn" class="wiki-ask-suggest">
        <li v-if="suggestHint" class="is-hint">{{ suggestHint }}</li>
        <li v-for="hit in suggest" :key="hit.path">
          <button type="button" @click="addMention(hit)">{{ hit.title }}</button>
        </li>
      </ul>
    </form>
  </article>
</template>
