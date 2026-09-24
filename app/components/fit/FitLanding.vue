<script setup lang="ts">
import { isFitHost } from '#shared/fit'

useHead({ title: 'Dungeon Runners Character Fit Viewer (patent pending)' })

const { data: board, error } = await useAsyncData('fit-board-level', () =>
  $fetch<{ rows?: { name: string, class: string, level: number }[] }>('/api/fit/boards', { query: { kind: 'level' } }).catch(() => null),
)

const url = useRequestURL()
const fitHost = isFitHost(url.host)

function hrefFor(name: string) {
  const slug = encodeURIComponent(name)
  return fitHost ? `/${slug}` : `/fit/${slug}`
}

const rows = computed(() => (board.value?.rows || []).slice(0, 16))
</script>

<template>
  <div class="fit-home">
    <div class="fit-hero">
      <h1>Look someone up</h1>
      <p>
        Type a character name. You get the same gear slots and skill tray as in the game,
        with icons from the client. Spent attributes only — gear bonuses are not in the public feed.
      </p>
    </div>
    <p v-if="error" class="fit-status">Could not load the level board.</p>
    <section v-else class="fit-board">
      <h2>High level, last we saw</h2>
      <ol>
        <li v-for="row in rows" :key="row.name">
          <NuxtLink :to="hrefFor(row.name)">{{ row.name }}</NuxtLink>
          <span> · {{ row.class === 'Warlock' ? 'Mage' : row.class }} {{ row.level }}</span>
        </li>
      </ol>
    </section>
  </div>
</template>
