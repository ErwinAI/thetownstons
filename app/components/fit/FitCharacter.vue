<script setup lang="ts">
import { GEAR_SLOTS, HOTBAR_SLOTS, isFitHost, normalizeCharName } from '#shared/fit'
import { formatGold, formatPlayed, formatWhen, type FitSeriesPoint, type FitSession } from '#shared/fit-xp'

type FitCharView = {
  name: string
  level: number
  classLabel: string
  attributes: { key: string, label: string, value: number }[]
  bySlot: Record<number, { name: string, qualityClass: string, lines: string[], wiki: string | null, icon: string | null, twoHanded?: boolean }>
  bySkillSlot: Record<number, { name: string, level: number, description: string | null, cooldown: number | null, mana: number | null, icon: string | null, wiki: string | null }>
  gold: number | null
  playedSeconds: number | null
  fetchedAt: string
  source: 'live' | 'cache' | 'history'
  prevAt: string | null
  nextAt: string | null
  nextFetchAt: string | null
}

const props = defineProps<{ name?: string }>()
const route = useRoute()
const rawName = computed(() => {
  const fromProp = props.name
  const param = fromProp
    ?? (Array.isArray(route.params.name) ? route.params.name[0] : String(route.params.name || ''))
  try {
    return normalizeCharName(decodeURIComponent(String(param || '')))
  }
  catch {
    return normalizeCharName(String(param || ''))
  }
})
const at = computed(() => String(route.query.at || ''))

useHead({
  title: () => rawName.value || 'Character',
})

const { data, error, pending, refresh } = await useAsyncData(
  () => 'fit-char-' + (rawName.value || '') + '-' + at.value,
  () => {
    if (!rawName.value) return Promise.resolve(null)
    return $fetch<FitCharView>(`/api/fit/character/${encodeURIComponent(rawName.value)}`, {
      query: at.value ? { at: at.value } : {},
    })
  },
)

const { data: progress } = await useAsyncData(
  () => 'fit-progress-' + (rawName.value || ''),
  () => {
    if (!rawName.value) return Promise.resolve({ series: [] as FitSeriesPoint[], sessions: [] as FitSession[] })
    return $fetch<{ series: FitSeriesPoint[], sessions: FitSession[] }>(
      `/api/fit/character/${encodeURIComponent(rawName.value)}/progress`,
    )
  },
)

watch(at, () => { refresh() })

const tip = ref<{
  x: number
  y: number
  title: string
  klass: string
  lines: string[]
  body?: string | null
} | null>(null)
let hideTimer: ReturnType<typeof setTimeout> | null = null

function keepTip() {
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
}

function hideTipSoon() {
  keepTip()
  hideTimer = setTimeout(() => { tip.value = null }, 80)
}

function placeTip(ev: MouseEvent) {
  const el = ev.currentTarget as HTMLElement | null
  const box = el?.getBoundingClientRect()
  const width = 380
  const left = box
    ? Math.min(box.right + 10, (typeof window !== 'undefined' ? window.innerWidth : 1200) - width - 12)
    : ev.clientX + 14
  const top = box
    ? Math.min(box.top, (typeof window !== 'undefined' ? window.innerHeight : 800) - 80)
    : ev.clientY + 14
  return { x: Math.max(8, left), y: Math.max(8, top) }
}

function showItem(ev: MouseEvent, item: { name: string, qualityClass: string, lines: string[], wiki: string | null } | undefined) {
  keepTip()
  if (!item) {
    tip.value = null
    return
  }
  tip.value = {
    ...placeTip(ev),
    title: item.name,
    klass: item.qualityClass,
    lines: item.lines,
  }
}

function showSkill(ev: MouseEvent, skill: { name: string, level: number, description: string | null, cooldown: number | null, mana: number | null, wiki?: string | null } | undefined) {
  keepTip()
  if (!skill) {
    tip.value = null
    return
  }
  const lines = [`Rank ${skill.level}`]
  if (skill.mana != null) lines.push(`Mana ${skill.mana}`)
  if (skill.cooldown != null) lines.push(`Cooldown ${skill.cooldown}s`)
  tip.value = {
    ...placeTip(ev),
    title: skill.name,
    klass: 'q-normal',
    lines,
    body: skill.description,
  }
}

function openWiki(ev: MouseEvent, wiki: string | null | undefined) {
  if (!wiki) return
  ev.preventDefault()
  window.open(wiki, '_blank', 'noopener')
}

const char = computed(() => data.value)
const url = useRequestURL()
const fitHost = isFitHost(url.host)
const home = fitHost ? '/' : '/fit/'

function sheetLink(when?: string | null) {
  const path = fitHost ? `/${encodeURIComponent(rawName.value || '')}` : `/fit/${encodeURIComponent(rawName.value || '')}`
  if (!when) return path
  return { path, query: { at: when } }
}

function rate(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return '—'
  return Math.round(n).toLocaleString()
}

function hours(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

const whenLabel = computed(() => {
  const row = char.value
  if (!row?.fetchedAt) return ''
  if (row.source === 'history') return `Sheet from ${formatWhen(row.fetchedAt)}`
  if (row.source === 'live') return `Fetched ${formatWhen(row.fetchedAt)}`
  return `Cached · last fetched ${formatWhen(row.fetchedAt)}`
})

type SlotItem = { name: string, qualityClass: string, lines: string[], wiki: string | null, icon: string | null, twoHanded?: boolean }

const slotViews = computed(() => {
  const sheet = char.value
  const out: Record<number, { item: SlotItem | undefined, ghost: boolean }> = {}
  for (const slot of GEAR_SLOTS) {
    const item = sheet?.bySlot[slot.id]
    if (item) {
      out[slot.id] = { item, ghost: false }
      continue
    }
    if (slot.id === 11 && sheet?.bySlot[10]?.twoHanded) {
      out[slot.id] = { item: sheet.bySlot[10], ghost: true }
      continue
    }
    out[slot.id] = { item: undefined, ghost: false }
  }
  return out
})
</script>

<template>
  <div>
    <p v-if="!rawName" class="fit-error">That name is not valid.</p>
    <p v-else-if="pending && !char" class="fit-status">Pulling the sheet…</p>
    <p v-else-if="error" class="fit-error">
      {{ error.statusCode === 404 ? 'Nobody public by that name.' : 'Could not load that character.' }}
      <NuxtLink :to="home">Back</NuxtLink>
    </p>
    <div v-else-if="char">
      <div class="fit-history">
        <NuxtLink v-if="char.prevAt" class="fit-btn" :to="sheetLink(char.prevAt)">Older</NuxtLink>
        <span v-else class="fit-btn disabled">Older</span>
        <div class="fit-when">
          <strong>{{ whenLabel }}</strong>
          <span v-if="char.nextFetchAt && char.source !== 'history'">
            Next crawl {{ formatWhen(char.nextFetchAt) }}
          </span>
          <NuxtLink v-if="char.source === 'history'" :to="sheetLink()">Latest</NuxtLink>
        </div>
        <NuxtLink v-if="char.nextAt" class="fit-btn" :to="sheetLink(char.nextAt)">Newer</NuxtLink>
        <span v-else class="fit-btn disabled">Newer</span>
      </div>

      <div class="fit-sheet">
        <div class="fit-nameplate">
          <strong>{{ char.name }}</strong>
          <span>Level {{ char.level }} {{ char.classLabel }}</span>
        </div>

        <div class="fit-equip">
          <div
            v-for="slot in GEAR_SLOTS"
            :key="slot.id"
            class="fit-slot"
            :class="[
              `fit-slot-${slot.key}`,
              slotViews[slot.id]?.item ? 'has-item' : 'is-empty',
              slotViews[slot.id]?.ghost ? 'is-ghost' : '',
            ]"
            :title="slotViews[slot.id]?.ghost
              ? `${slotViews[slot.id]?.item?.name || ''} (2H)`
              : (slotViews[slot.id]?.item?.name || slot.label)"
            @mouseenter="showItem($event, slotViews[slot.id]?.item)"
            @mouseleave="hideTipSoon"
            @click="openWiki($event, slotViews[slot.id]?.item?.wiki)"
          >
            <img
              v-if="slotViews[slot.id]?.item?.icon"
              :src="slotViews[slot.id]?.item?.icon || ''"
              :alt="slotViews[slot.id]?.item?.name || ''"
            >
          </div>
        </div>

        <aside class="fit-stats">
          <h2>Attributes spent</h2>
          <div class="fit-attr">
            <template v-for="row in char.attributes" :key="row.key">
              <span>{{ row.label }}</span>
              <span>{{ row.value }}</span>
            </template>
          </div>
          <div class="fit-meta">
            <span>Gold</span>
            <span>{{ formatGold(char.gold) }}</span>
            <span>Played</span>
            <span>{{ formatPlayed(char.playedSeconds) }}</span>
          </div>
          <p class="fit-note">
            Spent points only, before gear. Gold and play time come from the public boards when they show this name.
          </p>
        </aside>

        <div class="fit-hotbar-wrap">
          <div class="fit-hotbar">
            <div
              v-for="slot in HOTBAR_SLOTS"
              :key="slot.id"
              class="fit-skill"
              :class="[`fit-skill-${slot.key}`, char.bySkillSlot[slot.id] ? 'has-item' : 'is-empty']"
              :title="char.bySkillSlot[slot.id]?.name || slot.key"
              @mouseenter="showSkill($event, char.bySkillSlot[slot.id])"
              @mouseleave="hideTipSoon"
              @click="openWiki($event, char.bySkillSlot[slot.id]?.wiki)"
            >
              <img
                v-if="char.bySkillSlot[slot.id]?.icon"
                :src="char.bySkillSlot[slot.id].icon"
                :alt="char.bySkillSlot[slot.id].name"
              >
              <span v-if="char.bySkillSlot[slot.id]" class="lvl">{{ char.bySkillSlot[slot.id].level }}</span>
            </div>
          </div>
        </div>
      </div>

      <ClientOnly>
        <FitCharts :series="progress?.series || []" />
      </ClientOnly>

      <section v-if="progress?.sessions?.length" class="fit-sessions">
        <h2>Sessions</h2>
        <p class="fit-note">
          Gold/hour and XP/hour between fetches where play time went up.
          XP is same-level 1.0-mob kills from the client Experience curve (sparse knots through 100, then the 75→100 slope).
          It only moves when they ding; sitting at 100 looks flat.
        </p>
        <table>
          <thead>
            <tr>
              <th>From</th>
              <th>To</th>
              <th>Hours</th>
              <th>Gold/hr</th>
              <th>XP/hr</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in progress.sessions" :key="row.from + row.to">
              <td>{{ formatWhen(row.from) }}</td>
              <td>{{ formatWhen(row.to) }}</td>
              <td>{{ hours(row.hours) }}</td>
              <td>{{ rate(row.goldPerHour) }}</td>
              <td>{{ rate(row.xpPerHour) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <div
      v-if="tip"
      class="fit-tip"
      :style="{ left: tip.x + 'px', top: tip.y + 'px' }"
    >
      <h3 :class="tip.klass">{{ tip.title }}</h3>
      <ul v-if="tip.lines.length">
        <li v-for="(line, i) in tip.lines" :key="i">{{ line }}</li>
      </ul>
      <p v-if="tip.body" class="fit-tip-body">{{ tip.body }}</p>
    </div>
  </div>
</template>
