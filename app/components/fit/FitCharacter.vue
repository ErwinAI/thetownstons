<script setup lang="ts">
import { GEAR_SLOTS, HOTBAR_SLOTS, isFitHost, normalizeCharName } from '#shared/fit'
import { formatGold, formatPlayed, formatWhen, type FitSeriesPoint, type FitSession } from '#shared/fit-xp'

type FitCharView = {
  name: string
  level: number
  classLabel: string
  attributes: { key: string, label: string, value: number }[]
  bySlot: Record<number, { name: string, qualityClass: string, lines: string[], wiki: string | null, icon: string | null }>
  bySkillSlot: Record<number, { name: string, level: number, description: string | null, cooldown: number | null, mana: number | null, icon: string | null }>
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

const tip = ref<{ x: number, y: number, title: string, klass: string, lines: string[], href?: string | null } | null>(null)

function showItem(ev: MouseEvent, item: { name: string, qualityClass: string, lines: string[], wiki: string | null } | undefined) {
  if (!item) {
    tip.value = null
    return
  }
  tip.value = {
    x: ev.clientX + 14,
    y: ev.clientY + 14,
    title: item.name,
    klass: item.qualityClass,
    lines: item.lines,
    href: item.wiki,
  }
}

function showSkill(ev: MouseEvent, skill: { name: string, level: number, description: string | null, cooldown: number | null, mana: number | null } | undefined) {
  if (!skill) {
    tip.value = null
    return
  }
  const lines = [`Rank ${skill.level}`]
  if (skill.mana != null) lines.push(`Mana ${skill.mana}`)
  if (skill.cooldown != null) lines.push(`Cooldown ${skill.cooldown}s`)
  if (skill.description) lines.push(skill.description)
  tip.value = { x: ev.clientX + 14, y: ev.clientY + 14, title: skill.name, klass: 'q-normal', lines }
}

function moveTip(ev: MouseEvent) {
  if (!tip.value) return
  tip.value = { ...tip.value, x: ev.clientX + 14, y: ev.clientY + 14 }
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

      <div class="fit-sheet" @mousemove="moveTip" @mouseleave="tip = null">
        <div class="fit-nameplate">
          <strong>{{ char.name }}</strong>
          <span>Level {{ char.level }} {{ char.classLabel }}</span>
        </div>

        <div class="fit-equip">
          <div
            v-for="slot in GEAR_SLOTS"
            :key="slot.id"
            class="fit-slot"
            :class="[`fit-slot-${slot.key}`, char.bySlot[slot.id] ? 'has-item' : 'is-empty']"
            :title="char.bySlot[slot.id]?.name || slot.label"
            @mouseenter="showItem($event, char.bySlot[slot.id])"
            @mouseleave="tip = null"
            @click="char.bySlot[slot.id]?.wiki && window.open(char.bySlot[slot.id].wiki, '_blank')"
          >
            <img
              v-if="char.bySlot[slot.id]?.icon"
              :src="char.bySlot[slot.id].icon"
              :alt="char.bySlot[slot.id].name"
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
              :title="char.bySkillSlot[slot.id]?.name || slot.key"
              @mouseenter="showSkill($event, char.bySkillSlot[slot.id])"
              @mouseleave="tip = null"
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
      :style="{ left: Math.min(tip.x, 900) + 'px', top: tip.y + 'px' }"
    >
      <h3 :class="tip.klass">{{ tip.title }}</h3>
      <ul>
        <li v-for="(line, i) in tip.lines" :key="i">{{ line }}</li>
      </ul>
    </div>
  </div>
</template>
