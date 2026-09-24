// Client Experience curve (Tables.gc). Value = same-level 1.0-mob kills to ding.
// Knots include the commented designer points; past 100 uses the 75→100 slope.

const KNOTS: [number, number][] = [
  [1, 10],
  [2, 10],
  [3, 25],
  [4, 45],
  [5, 65],
  [12, 160],
  [22, 365],
  [75, 1740],
  [100, 5000],
]

export function killsToNext(level: number): number {
  const n = Number(level)
  if (!Number.isFinite(n) || n < 1) return 0
  const first = KNOTS[0]
  const last = KNOTS[KNOTS.length - 1]
  const prev = KNOTS[KNOTS.length - 2]
  if (n <= first[0]) return first[1]
  if (n >= last[0]) {
    const slope = (last[1] - prev[1]) / (last[0] - prev[0])
    return last[1] + slope * (n - last[0])
  }
  for (let i = 1; i < KNOTS.length; i++) {
    const [l1, v1] = KNOTS[i - 1]
    const [l2, v2] = KNOTS[i]
    if (n <= l2) {
      const t = (n - l1) / (l2 - l1)
      return v1 + t * (v2 - v1)
    }
  }
  return last[1]
}

/** Cumulative mob-kills already spent to sit at `level` (start of that level). */
export function xpAtLevel(level: number): number {
  const n = Math.floor(Number(level) || 0)
  if (n <= 1) return 0
  let sum = 0
  for (let L = 1; L < n; L++) sum += killsToNext(L)
  return sum
}

export function formatPlayed(sec: number | null | undefined): string {
  if (sec == null || !Number.isFinite(sec)) return '—'
  const s = Math.max(0, Math.floor(sec))
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (d) return `${d}d ${h}h ${m}m`
  if (h) return `${h}h ${m}m`
  if (m) return `${m}m`
  return `${s}s`
}

export function formatGold(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return '—'
  return Math.round(n).toLocaleString()
}

export function formatWhen(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export type FitSeriesPoint = {
  at: string
  source: string
  level: number | null
  gold: number | null
  playedSeconds: number | null
  xp: number | null
}

export type FitSession = {
  from: string
  to: string
  hours: number
  playedDelta: number
  goldDelta: number | null
  goldPerHour: number | null
  xpDelta: number | null
  xpPerHour: number | null
}

export function sessionsFromSeries(points: FitSeriesPoint[]): FitSession[] {
  const out: FitSession[] = []
  const rows = points.filter((p) => p.playedSeconds != null).sort((a, b) => a.at.localeCompare(b.at))
  for (let i = 1; i < rows.length; i++) {
    const a = rows[i - 1]
    const b = rows[i]
    const playedDelta = (b.playedSeconds || 0) - (a.playedSeconds || 0)
    if (playedDelta < 60) continue
    const hours = playedDelta / 3600
    const goldDelta = a.gold != null && b.gold != null ? b.gold - a.gold : null
    const xpDelta = a.xp != null && b.xp != null ? b.xp - a.xp : null
    out.push({
      from: a.at,
      to: b.at,
      hours,
      playedDelta,
      goldDelta,
      goldPerHour: goldDelta == null ? null : goldDelta / hours,
      xpDelta,
      xpPerHour: xpDelta == null ? null : xpDelta / hours,
    })
  }
  return out.slice(-80).reverse()
}
