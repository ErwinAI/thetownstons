import { createHash } from 'node:crypto'
import { normalizeCharName } from '#shared/fit'
import { sessionsFromSeries, xpAtLevel, type FitSeriesPoint } from '#shared/fit-xp'
import { presentCharacter } from './fit'
import { serviceClient } from './supabase'

export const CHAR_UPSTREAM = 'https://play.dungeonrunnersreborn.com/api/v1/characters/'
export const BOARD_UPSTREAM = 'https://play.dungeonrunnersreborn.com/api'

const DAY_MS = 24 * 60 * 60 * 1000
const SHEET_MAX_AGE_MS = DAY_MS
const FETCH_GAP_MS = 550
const LOCK_MS = 4 * 60 * 1000
const mem = new Map<string, { at: number, payload: FitCharPayload }>()
const MEM_TTL_MS = 10 * 60 * 1000
let boardCache: { at: number, stats: Map<string, BoardStat> } | null = null

export type FitCharRow = {
  name_key: string
  display_name: string
  last_fetched_at: string | null
  next_fetch_at: string
  last_level: number | null
  last_gold: number | null
  last_played_seconds: number | null
  idle_streak: number
  last_etag: string | null
  payload_hash: string | null
  search_count?: number
  last_searched_at?: string | null
  og_hash?: string | null
  og_path?: string | null
  og_at?: string | null
}

export type FitSearchHit = {
  name: string
  count?: number
  at?: string | null
}

export type FitSnapshotRow = {
  id: number
  name_key: string
  fetched_at: string
  source: 'sheet' | 'board'
  level: number | null
  gold: number | null
  played_seconds: number | null
  body: Record<string, unknown> | null
}

export type BoardStat = {
  displayName: string
  klass: string | null
  level: number | null
  gold: number | null
  played: number | null
}

export type FitCharPayload = ReturnType<typeof presentCharacter> & {
  gold: number | null
  playedSeconds: number | null
  fetchedAt: string
  snapshotId: number | null
  source: 'live' | 'cache' | 'history'
  prevAt: string | null
  nextAt: string | null
  nextFetchAt: string | null
}

function db() {
  return serviceClient()
}

function nameKey(name: string) {
  return name.toLowerCase()
}

function jitterMs(key: string, span = 50 * 60 * 1000) {
  let h = 0
  for (const c of key) h = (h * 33 + c.charCodeAt(0)) >>> 0
  return h % span
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function sheetHash(body: Record<string, unknown>, gold: number | null, played: number | null) {
  const raw = JSON.stringify({
    level: body.level,
    class: body.class,
    spent: body.spent_attributes,
    equipment: body.equipment,
    skills: body.equipped_skills,
    gold,
    played,
  })
  return createHash('sha1').update(raw).digest('hex')
}

export function nextAfterFetch(opts: {
  first: boolean
  increased: boolean
  idleStreak: number
  nameKey: string
  now?: Date
}) {
  const now = opts.now || new Date()
  const j = jitterMs(opts.nameKey)
  if (opts.first || opts.increased) {
    return { idleStreak: 0, nextFetchAt: new Date(now.getTime() + DAY_MS + j) }
  }
  const streak = opts.idleStreak + 1
  if (streak < 2) return { idleStreak: streak, nextFetchAt: new Date(now.getTime() + DAY_MS + j) }
  if (streak === 2) return { idleStreak: streak, nextFetchAt: new Date(now.getTime() + 3 * DAY_MS + j) }
  return { idleStreak: streak, nextFetchAt: new Date(now.getTime() + 7 * DAY_MS + j) }
}

function activityIncreased(
  playedBefore: number | null,
  playedAfter: number | null,
  hashBefore: string | null,
  hashAfter: string,
) {
  if (playedAfter != null && playedBefore != null) return playedAfter > playedBefore
  if (playedAfter != null && playedBefore == null) return true
  return Boolean(hashBefore) && hashAfter !== hashBefore
}

async function fetchRes(url: string, headers: Record<string, string> = {}) {
  let last: Response | null = null
  for (let i = 0; i < 4; i++) {
    last = await fetch(url, { headers: { Accept: 'application/json', ...headers }, redirect: 'follow' })
    if (last.status !== 429 && last.status !== 503) return last
    const wait = Number(last.headers.get('retry-after') || 2) * 1000
    await sleep(Math.min(Math.max(wait, 1500), 8000))
  }
  return last!
}

export async function fetchBoardRows(kind: string) {
  const rows: Record<string, unknown>[] = []
  for (let page = 1; page <= 20; page++) {
    const url = page === 1
      ? `${BOARD_UPSTREAM}/${kind}`
      : `${BOARD_UPSTREAM}/${kind}?page=${page}`
    const res = await fetchRes(url)
    if (!res.ok) break
    const data = await res.json() as { rows?: Record<string, unknown>[] }
    const chunk = Array.isArray(data.rows) ? data.rows : []
    if (!chunk.length) break
    const first = String(chunk[0]?.name || '')
    if (page > 1 && rows.length && String(rows[0]?.name || '') === first) break
    rows.push(...chunk)
    if (chunk.length < 100) break
  }
  return rows
}

export function mergeBoardStats(groups: Record<string, unknown>[][]): Map<string, BoardStat> {
  const stats = new Map<string, BoardStat>()
  for (const group of groups) {
    for (const row of group) {
      const displayName = String(row.name || '')
      const key = nameKey(displayName)
      if (!key) continue
      const cur = stats.get(key) || {
        displayName,
        klass: row.class != null ? String(row.class) : null,
        level: null,
        gold: null,
        played: null,
      }
      if (row.level != null && Number.isFinite(Number(row.level))) cur.level = Number(row.level)
      if (row.gold != null && Number.isFinite(Number(row.gold))) cur.gold = Number(row.gold)
      if (row.played_seconds != null && Number.isFinite(Number(row.played_seconds))) {
        cur.played = Number(row.played_seconds)
      }
      if (row.class != null) cur.klass = String(row.class)
      cur.displayName = displayName || cur.displayName
      stats.set(key, cur)
    }
  }
  return stats
}

async function currentBoardStats() {
  if (boardCache && Date.now() - boardCache.at < 60_000) return boardCache.stats
  const groups = await Promise.all([
    fetchBoardRows('level'),
    fetchBoardRows('gold'),
    fetchBoardRows('played'),
  ])
  boardCache = { at: Date.now(), stats: mergeBoardStats(groups) }
  return boardCache.stats
}

async function upsertChar(row: Partial<FitCharRow> & { name_key: string, display_name: string }) {
  const client = db()
  if (!client) return
  await client.from('fit_chars').upsert(row, { onConflict: 'name_key' })
}

async function insertSnapshot(row: Omit<FitSnapshotRow, 'id'> & { id?: number }) {
  const client = db()
  if (!client) return null
  const { data, error } = await client.from('fit_snapshots').insert({
    name_key: row.name_key,
    fetched_at: row.fetched_at,
    source: row.source,
    level: row.level,
    gold: row.gold,
    played_seconds: row.played_seconds,
    body: row.body,
  }).select('id').single()
  if (error) {
    console.warn('[fit] snapshot insert', error.message)
    return null
  }
  return Number(data?.id || 0) || null
}

export async function getCharRow(name: string): Promise<FitCharRow | null> {
  const client = db()
  if (!client) return null
  const { data, error } = await client.from('fit_chars').select('*').eq('name_key', nameKey(name)).maybeSingle()
  if (error) {
    console.warn('[fit] char row', error.message)
    return null
  }
  return data as FitCharRow | null
}

export async function listSheetNeighbors(name: string, fetchedAt: string) {
  const client = db()
  if (!client) return { prevAt: null as string | null, nextAt: null as string | null }
  const key = nameKey(name)
  const [prev, next] = await Promise.all([
    client.from('fit_snapshots')
      .select('fetched_at')
      .eq('name_key', key)
      .eq('source', 'sheet')
      .lt('fetched_at', fetchedAt)
      .order('fetched_at', { ascending: false })
      .limit(1),
    client.from('fit_snapshots')
      .select('fetched_at')
      .eq('name_key', key)
      .eq('source', 'sheet')
      .gt('fetched_at', fetchedAt)
      .order('fetched_at', { ascending: true })
      .limit(1),
  ])
  return {
    prevAt: prev.data?.[0]?.fetched_at || null,
    nextAt: next.data?.[0]?.fetched_at || null,
  }
}

export async function loadHistory(name: string): Promise<{ series: FitSeriesPoint[], sessions: ReturnType<typeof sessionsFromSeries> }> {
  const client = db()
  if (!client) return { series: [], sessions: [] }
  const { data, error } = await client.from('fit_snapshots')
    .select('fetched_at, source, level, gold, played_seconds')
    .eq('name_key', nameKey(name))
    .order('fetched_at', { ascending: true })
    .limit(800)
  if (error || !data) return { series: [], sessions: [] }
  const series: FitSeriesPoint[] = data.map((row) => ({
    at: row.fetched_at,
    source: row.source,
    level: row.level,
    gold: row.gold,
    playedSeconds: row.played_seconds,
    xp: row.level != null ? xpAtLevel(row.level) : null,
  }))
  return { series, sessions: sessionsFromSeries(series) }
}

export async function loadSheetAt(name: string, at?: string): Promise<FitSnapshotRow | null> {
  const client = db()
  if (!client) return null
  const key = nameKey(name)
  if (at && /^\d+$/.test(at)) {
    const { data } = await client.from('fit_snapshots').select('*').eq('id', Number(at)).maybeSingle()
    const row = data as FitSnapshotRow | null
    if (row?.body) return row
    if (row) at = row.fetched_at
    else return null
  }
  let q = client.from('fit_snapshots')
    .select('*')
    .eq('name_key', key)
    .eq('source', 'sheet')
    .not('body', 'is', null)
    .order('fetched_at', { ascending: false })
    .limit(1)
  if (at) q = q.lte('fetched_at', at)
  const { data } = await q
  return ((data || [])[0] as FitSnapshotRow | undefined) || null
}

function pack(
  body: Record<string, unknown>,
  extra: {
    gold: number | null
    playedSeconds: number | null
    fetchedAt: string
    snapshotId: number | null
    source: FitCharPayload['source']
    prevAt: string | null
    nextAt: string | null
    nextFetchAt: string | null
  },
): FitCharPayload {
  return {
    ...presentCharacter(body),
    gold: extra.gold,
    playedSeconds: extra.playedSeconds,
    fetchedAt: extra.fetchedAt,
    snapshotId: extra.snapshotId,
    source: extra.source,
    prevAt: extra.prevAt,
    nextAt: extra.nextAt,
    nextFetchAt: extra.nextFetchAt,
  }
}

function remember(name: string, payload: FitCharPayload) {
  if (payload.source !== 'history') {
    mem.set(nameKey(name), { at: Date.now(), payload })
    if (mem.size > 400) {
      const first = mem.keys().next().value
      if (first) mem.delete(first)
    }
  }
  return payload
}

export async function fetchUpstreamSheet(name: string, etag?: string | null) {
  const headers: Record<string, string> = {}
  if (etag) headers['If-None-Match'] = etag
  const res = await fetchRes(CHAR_UPSTREAM + encodeURIComponent(name), headers)
  return res
}

export async function saveLiveSheet(
  name: string,
  body: Record<string, unknown>,
  opts: { etag: string, gold: number | null, played: number | null, charRow: FitCharRow | null },
) {
  const key = nameKey(String(body.name || name))
  const display = String(body.name || name)
  const level = Number(body.level || 0)
  const gold = opts.gold ?? opts.charRow?.last_gold ?? null
  const played = opts.played ?? opts.charRow?.last_played_seconds ?? null
  const hash = sheetHash(body, gold, played)
  const first = !opts.charRow?.last_fetched_at
  const increased = activityIncreased(
    opts.charRow?.last_played_seconds ?? null,
    played,
    opts.charRow?.payload_hash ?? null,
    hash,
  )
  const sched = nextAfterFetch({
    first,
    increased,
    idleStreak: opts.charRow?.idle_streak || 0,
    nameKey: key,
  })
  const now = new Date().toISOString()
  await upsertChar({
    name_key: key,
    display_name: display,
    last_fetched_at: now,
    next_fetch_at: sched.nextFetchAt.toISOString(),
    last_level: level || opts.charRow?.last_level || null,
    last_gold: gold,
    last_played_seconds: played,
    idle_streak: sched.idleStreak,
    last_etag: opts.etag || opts.charRow?.last_etag || null,
    payload_hash: hash,
  })
  let snapshotId: number | null = null
  if (hash !== opts.charRow?.payload_hash) {
    snapshotId = await insertSnapshot({
      name_key: key,
      fetched_at: now,
      source: 'sheet',
      level: level || null,
      gold,
      played_seconds: played,
      body,
    })
  }
  if (hash !== opts.charRow?.og_hash) {
    const { captureFitOgSafe } = await import('./fit-og')
    void captureFitOgSafe(key, hash, body, gold, played)
  }
  return { now, snapshotId, nextFetchAt: sched.nextFetchAt.toISOString(), gold, played }
}

export async function getCharacterView(name: string, at?: string): Promise<FitCharPayload> {
  const pretty = normalizeCharName(name)
  if (!pretty) {
    throw createError({ statusCode: 400, statusMessage: 'Bad character name' })
  }

  if (!at) {
    const hit = mem.get(nameKey(pretty))
    if (hit && Date.now() - hit.at < MEM_TTL_MS) return hit.payload
  }

  if (at) {
    const snap = await loadSheetAt(pretty, at)
    if (!snap?.body) {
      throw createError({ statusCode: 404, statusMessage: 'No saved sheet at that time' })
    }
    const neigh = await listSheetNeighbors(pretty, snap.fetched_at)
    const row = await getCharRow(pretty)
    return pack(snap.body, {
      gold: snap.gold,
      playedSeconds: snap.played_seconds,
      fetchedAt: snap.fetched_at,
      snapshotId: snap.id,
      source: 'history',
      prevAt: neigh.prevAt,
      nextAt: neigh.nextAt,
      nextFetchAt: row?.next_fetch_at || null,
    })
  }

  const row = await getCharRow(pretty)
  const latest = await loadSheetAt(pretty, undefined)
  const fresh = latest?.body && latest.fetched_at
    && Date.now() - new Date(latest.fetched_at).getTime() < SHEET_MAX_AGE_MS

  if (fresh && latest.body) {
    const neigh = await listSheetNeighbors(pretty, latest.fetched_at)
    return remember(pretty, pack(latest.body, {
      gold: latest.gold ?? row?.last_gold ?? null,
      playedSeconds: latest.played_seconds ?? row?.last_played_seconds ?? null,
      fetchedAt: latest.fetched_at,
      snapshotId: latest.id,
      source: 'cache',
      prevAt: neigh.prevAt,
      nextAt: neigh.nextAt,
      nextFetchAt: row?.next_fetch_at || null,
    }))
  }

  const due = !row?.next_fetch_at || new Date(row.next_fetch_at).getTime() <= Date.now()
  if (latest?.body && !due) {
    const neigh = await listSheetNeighbors(pretty, latest.fetched_at)
    return remember(pretty, pack(latest.body, {
      gold: latest.gold ?? row?.last_gold ?? null,
      playedSeconds: latest.played_seconds ?? row?.last_played_seconds ?? null,
      fetchedAt: latest.fetched_at,
      snapshotId: latest.id,
      source: 'cache',
      prevAt: neigh.prevAt,
      nextAt: neigh.nextAt,
      nextFetchAt: row?.next_fetch_at || null,
    }))
  }

  const res = await fetchUpstreamSheet(pretty, row?.last_etag)
  if (res.status === 404) {
    throw createError({ statusCode: 404, statusMessage: 'No public character under that name' })
  }
  if (res.status === 304 && latest?.body) {
    const saved = await saveLiveSheet(pretty, latest.body, {
      etag: row?.last_etag || '',
      gold: row?.last_gold ?? null,
      played: row?.last_played_seconds ?? null,
      charRow: row,
    })
    const neigh = await listSheetNeighbors(pretty, latest.fetched_at)
    return remember(pretty, pack(latest.body, {
      gold: saved.gold,
      playedSeconds: saved.played,
      fetchedAt: latest.fetched_at,
      snapshotId: latest.id,
      source: 'cache',
      prevAt: neigh.prevAt,
      nextAt: neigh.nextAt,
      nextFetchAt: saved.nextFetchAt,
    }))
  }
  if (!res.ok) {
    if (latest?.body) {
      const neigh = await listSheetNeighbors(pretty, latest.fetched_at)
      return remember(pretty, pack(latest.body, {
        gold: latest.gold ?? row?.last_gold ?? null,
        playedSeconds: latest.played_seconds ?? row?.last_played_seconds ?? null,
        fetchedAt: latest.fetched_at,
        snapshotId: latest.id,
        source: 'cache',
        prevAt: neigh.prevAt,
        nextAt: neigh.nextAt,
        nextFetchAt: row?.next_fetch_at || null,
      }))
    }
    throw createError({ statusCode: res.status, statusMessage: `Character API HTTP ${res.status}` })
  }

  const body = await res.json() as Record<string, unknown>
  const boards = await currentBoardStats()
  const st = boards.get(nameKey(String(body.name || pretty)))
  const saved = await saveLiveSheet(String(body.name || pretty), body, {
    etag: res.headers.get('etag') || '',
    gold: st?.gold ?? row?.last_gold ?? null,
    played: st?.played ?? row?.last_played_seconds ?? null,
    charRow: row,
  })
  const fetchedAt = saved.now
  const neigh = await listSheetNeighbors(String(body.name || pretty), fetchedAt)
  return remember(pretty, pack(body, {
    gold: saved.gold,
    playedSeconds: saved.played,
    fetchedAt,
    snapshotId: saved.snapshotId,
    source: 'live',
    prevAt: neigh.prevAt,
    nextAt: null,
    nextFetchAt: saved.nextFetchAt,
  }))
}

async function acquireLock() {
  const client = db()
  if (!client) return true
  const { data } = await client.from('fit_meta').select('value, updated_at').eq('key', 'cron_lock').maybeSingle()
  if (data?.value && (data.value as { running?: boolean }).running) {
    const age = Date.now() - new Date(data.updated_at).getTime()
    if (age < LOCK_MS) return false
  }
  await client.from('fit_meta').upsert({
    key: 'cron_lock',
    value: { running: true },
    updated_at: new Date().toISOString(),
  })
  return true
}

async function releaseLock() {
  const client = db()
  if (!client) return
  await client.from('fit_meta').upsert({
    key: 'cron_lock',
    value: { running: false },
    updated_at: new Date().toISOString(),
  })
}

export async function runFitCrawl(opts?: { batch?: number, budgetMs?: number }) {
  const client = db()
  if (!client) return { ok: false, error: 'supabase missing' }
  if (!(await acquireLock())) return { ok: true, skipped: true, reason: 'locked' }

  const started = Date.now()
  const budgetMs = opts?.budgetMs ?? 48_000
  const batchCap = opts?.batch ?? 20
  try {
    const [level, gold, played, pvp] = await Promise.all([
      fetchBoardRows('level'),
      fetchBoardRows('gold'),
      fetchBoardRows('played'),
      fetchBoardRows('pvp'),
    ])
    const stats = mergeBoardStats([level, gold, played, pvp])
    const keys = [...stats.keys()]
    const existing = new Set<string>()
    for (let i = 0; i < keys.length; i += 80) {
      const chunk = keys.slice(i, i + 80)
      const { data } = await client.from('fit_chars').select('name_key').in('name_key', chunk)
      for (const row of data || []) existing.add(row.name_key)
    }

    const inserts: Partial<FitCharRow>[] = []
    let i = 0
    for (const [key, st] of stats) {
      if (existing.has(key)) continue
      const slot = i % 24
      inserts.push({
        name_key: key,
        display_name: st.displayName,
        next_fetch_at: new Date(Date.now() + slot * 3600_000 + jitterMs(key)).toISOString(),
        last_level: st.level,
        last_gold: st.gold,
        last_played_seconds: st.played,
        idle_streak: 0,
      })
      i += 1
    }
    for (let n = 0; n < inserts.length; n += 50) {
      await client.from('fit_chars').upsert(inserts.slice(n, n + 50))
    }

    let boardSnaps = 0
    const known = await client.from('fit_chars').select('name_key, last_level, last_gold, last_played_seconds, display_name').in('name_key', keys)
    const byKey = new Map((known.data || []).map((r) => [r.name_key, r]))
    const boardRows: Omit<FitSnapshotRow, 'id'>[] = []
    const charPatches: Partial<FitCharRow>[] = []
    const nowIso = new Date().toISOString()
    for (const [key, st] of stats) {
      const prev = byKey.get(key)
      const changed = !prev
        || prev.last_level !== st.level
        || prev.last_gold !== st.gold
        || prev.last_played_seconds !== st.played
      if (!changed) continue
      boardRows.push({
        name_key: key,
        fetched_at: nowIso,
        source: 'board',
        level: st.level,
        gold: st.gold,
        played_seconds: st.played,
        body: null,
      })
      charPatches.push({
        name_key: key,
        display_name: st.displayName || prev?.display_name || key,
        last_level: st.level,
        last_gold: st.gold,
        last_played_seconds: st.played,
      })
    }
    for (let n = 0; n < boardRows.length; n += 50) {
      const { error } = await client.from('fit_snapshots').insert(boardRows.slice(n, n + 50))
      if (!error) boardSnaps += boardRows.slice(n, n + 50).length
    }
    for (const patch of charPatches) {
      await client.from('fit_chars').update({
        last_level: patch.last_level,
        last_gold: patch.last_gold,
        last_played_seconds: patch.last_played_seconds,
        display_name: patch.display_name,
      }).eq('name_key', patch.name_key)
    }

    const due = await client.from('fit_chars')
      .select('*')
      .lte('next_fetch_at', new Date().toISOString())
      .order('next_fetch_at', { ascending: true })
      .limit(Math.max(batchCap, 80))
    if (due.error) return { ok: false, error: due.error.message }

    let fetched = 0
    let failed = 0
    const dueRows = (due.data || []) as FitCharRow[]
    for (const char of dueRows) {
      if (fetched >= batchCap && Date.now() - started > budgetMs) break
      if (Date.now() - started > budgetMs) break
      if (fetched) await sleep(FETCH_GAP_MS)
      const st = stats.get(char.name_key)
      try {
        const res = await fetchUpstreamSheet(char.display_name, char.last_etag)
        if (res.status === 404) {
          await client.from('fit_chars').update({
            next_fetch_at: new Date(Date.now() + 7 * DAY_MS).toISOString(),
            idle_streak: Math.max(char.idle_streak, 3),
          }).eq('name_key', char.name_key)
          failed += 1
          continue
        }
        if (res.status === 304) {
          const hash = char.payload_hash || 'same'
          const played = st?.played ?? char.last_played_seconds
          const gold = st?.gold ?? char.last_gold
          const sched = nextAfterFetch({
            first: false,
            increased: activityIncreased(char.last_played_seconds, played ?? null, char.payload_hash, hash),
            idleStreak: char.idle_streak,
            nameKey: char.name_key,
          })
          await client.from('fit_chars').update({
            last_fetched_at: new Date().toISOString(),
            next_fetch_at: sched.nextFetchAt.toISOString(),
            idle_streak: sched.idleStreak,
            last_gold: gold,
            last_played_seconds: played,
          }).eq('name_key', char.name_key)
          fetched += 1
          continue
        }
        if (!res.ok) {
          failed += 1
          continue
        }
        const body = await res.json() as Record<string, unknown>
        await saveLiveSheet(String(body.name || char.display_name), body, {
          etag: res.headers.get('etag') || '',
          gold: st?.gold ?? char.last_gold ?? null,
          played: st?.played ?? char.last_played_seconds ?? null,
          charRow: char,
        })
        fetched += 1
      }
      catch (err) {
        failed += 1
        console.warn('[fit] crawl', char.display_name, err)
      }
    }

    return {
      ok: true,
      boards: { level: level.length, gold: gold.length, played: played.length, pvp: pvp.length, unique: stats.size },
      enrolled: inserts.length,
      boardSnaps,
      due: dueRows.length,
      fetched,
      failed,
      ms: Date.now() - started,
    }
  }
  finally {
    await releaseLock()
  }
}

let searchTables = true

export async function recordFitSearch(name: string) {
  const pretty = normalizeCharName(name)
  if (!pretty) return
  const client = db()
  if (!client) return
  const key = nameKey(pretty)
  if (searchTables) {
    const { error } = await client.rpc('record_fit_search', {
      p_name_key: key,
      p_display_name: pretty,
    })
    if (!error) return
    searchTables = false
  }

  const now = new Date().toISOString()
  const countKey = `search:${key}`
  const { data: row } = await client.from('fit_meta').select('value').eq('key', countKey).maybeSingle()
  const prev = (row?.value || {}) as { count?: number }
  const { error: countErr } = await client.from('fit_meta').upsert({
    key: countKey,
    value: { count: Number(prev.count || 0) + 1, display_name: pretty, last: now },
    updated_at: now,
  })
  if (countErr) {
    console.warn('[fit] search count', error.message, countErr.message)
    return
  }
  const { data: logRow } = await client.from('fit_meta').select('value').eq('key', 'search_log').maybeSingle()
  const log = Array.isArray(logRow?.value) ? logRow.value as { name_key: string, display_name: string, searched_at: string }[] : []
  log.unshift({ name_key: key, display_name: pretty, searched_at: now })
  const { error: logErr } = await client.from('fit_meta').upsert({
    key: 'search_log',
    value: log.slice(0, 40),
    updated_at: now,
  })
  if (logErr) console.warn('[fit] search log', logErr.message)
}

function uniquifyRecent(rows: FitSearchHit[]): FitSearchHit[] {
  const out: FitSearchHit[] = []
  const seen = new Set<string>()
  for (const row of rows) {
    const k = row.name.toLowerCase()
    if (seen.has(k)) continue
    seen.add(k)
    out.push(row)
    if (out.length >= 10) break
  }
  return out
}

export async function listFitSearches(): Promise<{ top: FitSearchHit[], recent: FitSearchHit[] }> {
  const empty = { top: [] as FitSearchHit[], recent: [] as FitSearchHit[] }
  const client = db()
  if (!client) return empty

  if (searchTables) {
    const { data: topRows, error: topErr } = await client
      .from('fit_chars')
      .select('display_name, search_count, last_searched_at')
      .gt('search_count', 0)
      .order('search_count', { ascending: false })
      .limit(10)
    if (topErr) searchTables = false
    else {
      const { data: logRows } = await client
        .from('fit_search_log')
        .select('display_name, searched_at')
        .order('searched_at', { ascending: false })
        .limit(40)
      return {
        top: (topRows || []).map((row) => ({
          name: String(row.display_name),
          count: Number(row.search_count || 0),
          at: row.last_searched_at || null,
        })),
        recent: uniquifyRecent((logRows || []).map((row) => ({
          name: String(row.display_name),
          at: row.searched_at || null,
        }))),
      }
    }
  }

  const { data: metas } = await client.from('fit_meta').select('key, value').like('key', 'search:%')
  const { data: logRow } = await client.from('fit_meta').select('value').eq('key', 'search_log').maybeSingle()
  const top = (metas || [])
    .map((row) => {
      const value = (row.value || {}) as { count?: number, display_name?: string, last?: string }
      return {
        name: String(value.display_name || String(row.key).slice('search:'.length)),
        count: Number(value.count || 0),
        at: value.last || null,
      }
    })
    .filter((row) => row.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, 10)
  const log = Array.isArray(logRow?.value) ? logRow.value as { display_name?: string, searched_at?: string }[] : []
  return {
    top,
    recent: uniquifyRecent(log.map((row) => ({
      name: String(row.display_name || ''),
      at: row.searched_at || null,
    })).filter((row) => row.name)),
  }
}
