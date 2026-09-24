<script setup lang="ts">
import type { FitSeriesPoint } from '#shared/fit-xp'

const props = defineProps<{ series: FitSeriesPoint[] }>()

const levelGold = ref<HTMLCanvasElement | null>(null)
const played = ref<HTMLCanvasElement | null>(null)
const charts: { destroy: () => void }[] = []

const ink = '#f3e6c4'
const muted = '#b9a078'
const gold = '#d4b056'
const line = '#4dc3ff'
const grid = 'rgba(92, 67, 24, 0.45)'

function labels(rows: FitSeriesPoint[]) {
  return rows.map((row) => {
    const d = new Date(row.at)
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  })
}

async function draw() {
  for (const chart of charts.splice(0)) chart.destroy()
  if (!import.meta.client) return
  const rows = props.series || []
  if (!rows.length || !levelGold.value || !played.value) return
  const {
    Chart,
    LineController,
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Legend,
    Tooltip,
    Filler,
  } = await import('chart.js')
  Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Legend, Tooltip, Filler)
  Chart.defaults.animation = false
  Chart.defaults.font.family = '"Trebuchet MS", "Gill Sans", "Segoe UI", sans-serif'
  Chart.defaults.color = muted

  const ticks = labels(rows)
  const common = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false as const,
    plugins: {
      legend: { labels: { color: ink, boxWidth: 12 } },
    },
    scales: {
      x: {
        ticks: { color: muted, maxRotation: 0, autoSkip: true, maxTicksLimit: 8 },
        grid: { color: grid },
      },
    },
  }

  charts.push(new Chart(levelGold.value, {
    type: 'line',
    data: {
      labels: ticks,
      datasets: [
        {
          label: 'Level',
          data: rows.map((r) => r.level),
          borderColor: gold,
          backgroundColor: 'transparent',
          yAxisID: 'y',
          tension: 0,
          pointRadius: 2,
        },
        {
          label: 'Gold',
          data: rows.map((r) => r.gold),
          borderColor: ink,
          backgroundColor: 'transparent',
          yAxisID: 'y1',
          tension: 0,
          pointRadius: 2,
        },
      ],
    },
    options: {
      ...common,
      scales: {
        ...common.scales,
        y: {
          ticks: { color: gold },
          grid: { color: grid },
          title: { display: true, text: 'Level', color: gold },
        },
        y1: {
          position: 'right',
          ticks: { color: ink },
          grid: { drawOnChartArea: false },
          title: { display: true, text: 'Gold', color: ink },
        },
      },
    },
  }))

  charts.push(new Chart(played.value, {
    type: 'line',
    data: {
      labels: ticks,
      datasets: [
        {
          label: 'Hours played',
          data: rows.map((r) => (r.playedSeconds == null ? null : Math.round(r.playedSeconds / 36) / 100)),
          borderColor: line,
          backgroundColor: 'rgba(77, 195, 255, 0.12)',
          fill: true,
          tension: 0,
          pointRadius: 2,
        },
      ],
    },
    options: {
      ...common,
      scales: {
        ...common.scales,
        y: {
          ticks: { color: line },
          grid: { color: grid },
          title: { display: true, text: 'Hours', color: line },
        },
      },
    },
  }))
}

onMounted(draw)
watch(() => props.series, draw, { deep: true })
onBeforeUnmount(() => {
  for (const chart of charts.splice(0)) chart.destroy()
})
</script>

<template>
  <div v-if="series.length" class="fit-charts">
    <div class="fit-chart">
      <h2>Level and gold</h2>
      <div class="fit-chart-frame">
        <canvas ref="levelGold" />
      </div>
    </div>
    <div class="fit-chart">
      <h2>Play time vs fetch</h2>
      <div class="fit-chart-frame">
        <canvas ref="played" />
      </div>
    </div>
  </div>
</template>
