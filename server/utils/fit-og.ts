import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { GEAR_SLOTS } from '#shared/fit'
import { formatGold, formatPlayed } from '#shared/fit-xp'
import { presentCharacter, type FitItemView } from './fit'
import { serviceClient } from './supabase'

export const OG_WIDTH = 1200
export const OG_HEIGHT = 630
export const OG_BUCKET = 'fit-og'

const EQUIP_SRC = { w: 365, h: 268 }
const STATS_SRC = { w: 367, h: 571 }
const NAMEPLATE_SRC = { w: 256, h: 128 }

const SLOT_BOX: Record<string, { l: number, t: number, w: number, h: number }> = {
  weapon: { l: 0.079, t: 0.187, w: 0.170, h: 0.466 },
  helm: { l: 0.312, t: 0.198, w: 0.162, h: 0.228 },
  shield: { l: 0.534, t: 0.194, w: 0.164, h: 0.459 },
  shoulders: { l: 0.751, t: 0.187, w: 0.173, h: 0.235 },
  armor: { l: 0.310, t: 0.496, w: 0.164, h: 0.451 },
  ring1: { l: 0.742, t: 0.515, w: 0.082, h: 0.119 },
  ring2: { l: 0.836, t: 0.515, w: 0.082, h: 0.119 },
  gloves: { l: 0.077, t: 0.709, w: 0.173, h: 0.235 },
  boots: { l: 0.532, t: 0.713, w: 0.164, h: 0.228 },
  amulet: { l: 0.751, t: 0.705, w: 0.173, h: 0.239 },
}

const uiCache = new Map<string, Buffer>()
let bucketReady = false

export type FitOgView = {
  name: string
  level: number
  classLabel: string
  attributes: { key: string, label: string, value: number }[]
  bySlot: Record<number, FitItemView>
  gold: number | null
  playedSeconds: number | null
}

function publicFile(rel: string) {
  return [
    join(process.cwd(), 'public', rel),
    join(process.cwd(), '.output', 'public', rel),
  ]
}

async function readPublic(rel: string): Promise<Buffer | null> {
  const hit = uiCache.get(rel)
  if (hit) return hit
  for (const p of publicFile(rel)) {
    try {
      const buf = await readFile(p)
      if (rel.startsWith('fit/ui/')) uiCache.set(rel, buf)
      return buf
    }
    catch {
      // try next
    }
  }
  try {
    const origin = String(useRuntimeConfig().public.fitSiteUrl || 'https://fit.thetownstons.com').replace(/\/$/, '')
    const res = await fetch(`${origin}/${rel}`)
    if (!res.ok) return null
    const buf = Buffer.from(await res.arrayBuffer())
    if (rel.startsWith('fit/ui/')) uiCache.set(rel, buf)
    return buf
  }
  catch {
    return null
  }
}

function escapeXml(text: string) {
  return text.replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&apos;',
  }[ch] || ch))
}

function iconRel(icon: string | null | undefined) {
  if (!icon) return null
  const path = icon.replace(/^\//, '').split('?')[0]
  if (!path.startsWith('fit/icons/')) return null
  return path
}

async function withOpacity(sharp: typeof import('sharp'), input: Buffer, opacity: number) {
  const { data, info } = await sharp(input).ensureAlpha().raw().toBuffer({ resolveWithObject: true })
  for (let i = 3; i < data.length; i += 4) data[i] = Math.round(data[i] * opacity)
  return sharp(data, { raw: { width: info.width, height: info.height, channels: 4 } }).png().toBuffer()
}

async function placeIcon(
  sharp: typeof import('sharp'),
  iconBuf: Buffer,
  box: { x: number, y: number, w: number, h: number },
  ghost: boolean,
) {
  const innerW = Math.max(2, Math.round(box.w * 0.9))
  const innerH = Math.max(2, Math.round(box.h * 0.9))
  let png = await sharp(iconBuf)
    .resize({ width: innerW, height: innerH, fit: 'inside', kernel: 'nearest' })
    .png()
    .toBuffer()
  if (ghost) png = await withOpacity(sharp, png, 0.4)
  const meta = await sharp(png).metadata()
  const iw = meta.width || innerW
  const ih = meta.height || innerH
  return {
    input: png,
    left: box.x + Math.round((box.w - iw) / 2),
    top: box.y + Math.round((box.h - ih) / 2),
  }
}

export async function renderFitOgPng(view: FitOgView): Promise<Buffer> {
  const sharp = (await import('sharp')).default
  const [nameplate, equip, stats] = await Promise.all([
    readPublic('fit/ui/nameplate.png'),
    readPublic('fit/ui/equip.png'),
    readPublic('fit/ui/stats.png'),
  ])
  if (!nameplate || !equip || !stats) {
    throw new Error('Fit UI frames missing')
  }

  const leftW = 540
  const originX = 132
  const originY = 32
  const nameplateW = 340
  const nameplateH = Math.round(nameplateW * NAMEPLATE_SRC.h / NAMEPLATE_SRC.w)
  const nameplateX = originX + Math.round((leftW - nameplateW) / 2)
  const nameplateY = originY
  const equipW = leftW
  const equipH = Math.round(equipW * EQUIP_SRC.h / EQUIP_SRC.w)
  const equipX = originX
  const equipY = nameplateY + nameplateH + 8
  const statsH = OG_HEIGHT - originY - 36
  const statsW = Math.round(statsH * STATS_SRC.w / STATS_SRC.h)
  const statsX = originX + leftW + 36
  const statsY = originY
  const bySlot = view.bySlot || {}

  const equipLayers = (await Promise.all(GEAR_SLOTS.map(async (slot) => {
    const box = SLOT_BOX[slot.key]
    if (!box) return null
    let item = bySlot[slot.id]
    let ghost = false
    if (!item && slot.id === 11 && bySlot[10]?.twoHanded) {
      item = bySlot[10]
      ghost = true
    }
    const rel = iconRel(item?.icon)
    if (!rel) return null
    const raw = await readPublic(rel)
    if (!raw) return null
    return placeIcon(sharp, raw, {
      x: Math.round(box.l * equipW),
      y: Math.round(box.t * equipH),
      w: Math.round(box.w * equipW),
      h: Math.round(box.h * equipH),
    }, ghost)
  }))).filter((row): row is { input: Buffer, left: number, top: number } => Boolean(row))

  const equipCard = await sharp(equip)
    .resize(equipW, equipH, { kernel: 'lanczos3' })
    .composite(equipLayers)
    .png()
    .toBuffer()

  const nameSvg = Buffer.from(`
    <svg width="${nameplateW}" height="${nameplateH}" xmlns="http://www.w3.org/2000/svg">
      <text x="50%" y="46%" text-anchor="middle" font-family="Trebuchet MS, Segoe UI, sans-serif"
        font-size="${view.name.length > 16 ? 22 : 26}" font-weight="700" fill="#f3e6c4">${escapeXml(view.name)}</text>
      <text x="50%" y="68%" text-anchor="middle" font-family="Trebuchet MS, Segoe UI, sans-serif"
        font-size="16" fill="#b9a078">${escapeXml(`Level ${view.level} ${view.classLabel}`)}</text>
    </svg>
  `)
  const nameCard = await sharp(nameplate)
    .resize(nameplateW, nameplateH)
    .composite([{ input: nameSvg, left: 0, top: 0 }])
    .png()
    .toBuffer()

  const attrLines = (view.attributes || []).map((row) =>
    `<tspan x="${Math.round(statsW * 0.14)}" dy="1.35em">${escapeXml(row.label)}</tspan>`,
  ).join('')
  const attrVals = (view.attributes || []).map((row) =>
    `<tspan x="${Math.round(statsW * 0.86)}" dy="1.35em" text-anchor="end">${escapeXml(String(row.value))}</tspan>`,
  ).join('')
  const statsSvg = Buffer.from(`
    <svg width="${statsW}" height="${statsH}" xmlns="http://www.w3.org/2000/svg">
      <text x="50%" y="${Math.round(statsH * 0.07)}" text-anchor="middle"
        font-family="Trebuchet MS, Segoe UI, sans-serif" font-size="18" fill="#d4b056">Attributes spent</text>
      <text y="${Math.round(statsH * 0.12)}" font-family="Trebuchet MS, Segoe UI, sans-serif"
        font-size="18" fill="#b9a078">${attrLines}</text>
      <text y="${Math.round(statsH * 0.12)}" font-family="Trebuchet MS, Segoe UI, sans-serif"
        font-size="18" fill="#ffffff">${attrVals}</text>
      <text x="${Math.round(statsW * 0.14)}" y="${Math.round(statsH * 0.42)}"
        font-family="Trebuchet MS, Segoe UI, sans-serif" font-size="18" fill="#b9a078">Gold</text>
      <text x="${Math.round(statsW * 0.86)}" y="${Math.round(statsH * 0.42)}" text-anchor="end"
        font-family="Trebuchet MS, Segoe UI, sans-serif" font-size="18" fill="#ffffff">${escapeXml(formatGold(view.gold))}</text>
      <text x="${Math.round(statsW * 0.14)}" y="${Math.round(statsH * 0.48)}"
        font-family="Trebuchet MS, Segoe UI, sans-serif" font-size="18" fill="#b9a078">Played</text>
      <text x="${Math.round(statsW * 0.86)}" y="${Math.round(statsH * 0.48)}" text-anchor="end"
        font-family="Trebuchet MS, Segoe UI, sans-serif" font-size="18" fill="#ffffff">${escapeXml(formatPlayed(view.playedSeconds))}</text>
    </svg>
  `)
  const statsCard = await sharp(stats)
    .resize(statsW, statsH)
    .composite([{ input: statsSvg, left: 0, top: 0 }])
    .png()
    .toBuffer()

  const mark = Buffer.from(`
    <svg width="${OG_WIDTH}" height="${OG_HEIGHT}" xmlns="http://www.w3.org/2000/svg">
      <text x="${OG_WIDTH - 28}" y="${OG_HEIGHT - 18}" text-anchor="end"
        font-family="Trebuchet MS, Segoe UI, sans-serif" font-size="14" fill="#8a6a28">Fit · thetownstons.com</text>
    </svg>
  `)

  return sharp({
    create: {
      width: OG_WIDTH,
      height: OG_HEIGHT,
      channels: 3,
      background: '#140a05',
    },
  })
    .composite([
      { input: nameCard, left: nameplateX, top: nameplateY },
      { input: equipCard, left: equipX, top: equipY },
      { input: statsCard, left: statsX, top: statsY },
      { input: mark, left: 0, top: 0 },
    ])
    .png()
    .toBuffer()
}

export function ogObjectPath(nameKey: string, hash: string) {
  return `chars/${nameKey}/${hash}.png`
}

export function ogPublicUrl(path: string) {
  const client = serviceClient()
  if (!client) return null
  return client.storage.from(OG_BUCKET).getPublicUrl(path).data.publicUrl
}

async function ensureOgBucket() {
  if (bucketReady) return
  const client = serviceClient()
  if (!client) return
  const { data } = await client.storage.getBucket(OG_BUCKET)
  if (!data) {
    const { error } = await client.storage.createBucket(OG_BUCKET, {
      public: true,
      fileSizeLimit: 2 * 1024 * 1024,
      allowedMimeTypes: ['image/png'],
    })
    if (error && !/already exists|duplicate/i.test(error.message)) {
      console.warn('[fit] og bucket', error.message)
      return
    }
  }
  bucketReady = true
}

export async function loadDefaultOg(): Promise<Buffer | null> {
  return readPublic('fit/og-default.png')
}

export async function loadStoredOg(nameKey: string, hash: string): Promise<{ path: string, publicUrl: string, bytes: Buffer } | null> {
  const client = serviceClient()
  if (!client) return null
  const path = ogObjectPath(nameKey, hash)
  const { data, error } = await client.storage.from(OG_BUCKET).download(path)
  if (error || !data) return null
  const bytes = Buffer.from(await data.arrayBuffer())
  return { path, publicUrl: ogPublicUrl(path) || '', bytes }
}

export async function captureFitOgFromBody(
  nameKey: string,
  hash: string,
  body: Record<string, unknown>,
  gold: number | null,
  played: number | null,
) {
  const existing = await loadStoredOg(nameKey, hash)
  if (existing) return { path: existing.path, bytes: existing.bytes }

  const presented = presentCharacter(body)
  const png = await renderFitOgPng({
    name: presented.name,
    level: presented.level,
    classLabel: presented.classLabel,
    attributes: presented.attributes,
    bySlot: presented.bySlot,
    gold,
    playedSeconds: played,
  })
  const client = serviceClient()
  if (!client) return { path: null as string | null, bytes: png }
  await ensureOgBucket()
  const path = ogObjectPath(nameKey, hash)
  const { error } = await client.storage.from(OG_BUCKET).upload(path, png, {
    contentType: 'image/png',
    cacheControl: '31536000',
    upsert: true,
  })
  if (error) {
    console.warn('[fit] og upload', error.message)
    return { path: null, bytes: png }
  }
  await client.storage.from(OG_BUCKET).upload(`chars/${nameKey}/latest.png`, png, {
    contentType: 'image/png',
    cacheControl: '3600',
    upsert: true,
  })
  const now = new Date().toISOString()
  const { error: rowErr } = await client.from('fit_chars').update({
    og_hash: hash,
    og_path: path,
    og_at: now,
  }).eq('name_key', nameKey)
  if (rowErr) {
    await client.from('fit_meta').upsert({
      key: `og:${nameKey}`,
      value: { hash, path, at: now },
      updated_at: now,
    })
  }
  return { path, bytes: png }
}

export async function captureFitOgSafe(
  nameKey: string,
  hash: string,
  body: Record<string, unknown>,
  gold: number | null,
  played: number | null,
) {
  try {
    return await captureFitOgFromBody(nameKey, hash, body, gold, played)
  }
  catch (err) {
    console.warn('[fit] og capture', err)
    return null
  }
}

export async function runFitOgBackfill(opts?: { batch?: number, budgetMs?: number }) {
  const client = serviceClient()
  if (!client) return { ok: false, error: 'supabase missing' }
  const started = Date.now()
  const budgetMs = opts?.budgetMs ?? 50_000
  const batch = Math.min(Math.max(opts?.batch || 12, 1), 40)
  let q = await client
    .from('fit_chars')
    .select('name_key, display_name, payload_hash, og_hash, last_gold, last_played_seconds, last_fetched_at')
    .not('payload_hash', 'is', null)
    .order('last_fetched_at', { ascending: false })
    .limit(120)
  if (q.error) {
    q = await client
      .from('fit_chars')
      .select('name_key, display_name, payload_hash, last_gold, last_played_seconds, last_fetched_at')
      .not('payload_hash', 'is', null)
      .order('last_fetched_at', { ascending: false })
      .limit(120)
  }
  const rows = (q.data || []) as {
    name_key: string
    display_name: string
    payload_hash: string | null
    og_hash?: string | null
    last_gold: number | null
    last_played_seconds: number | null
  }[]
  let made = 0
  let skipped = 0
  let failed = 0
  for (const row of rows) {
    if (made >= batch || Date.now() - started > budgetMs) break
    const hash = row.payload_hash
    if (!hash) continue
    if (row.og_hash && row.og_hash === hash) {
      skipped += 1
      continue
    }
    const stored = await loadStoredOg(row.name_key, hash)
    if (stored) {
      skipped += 1
      continue
    }
    const { data: snaps } = await client
      .from('fit_snapshots')
      .select('body, gold, played_seconds')
      .eq('name_key', row.name_key)
      .eq('source', 'sheet')
      .not('body', 'is', null)
      .order('fetched_at', { ascending: false })
      .limit(1)
    const snap = snaps?.[0] as { body: Record<string, unknown> | null, gold: number | null, played_seconds: number | null } | undefined
    if (!snap?.body) {
      skipped += 1
      continue
    }
    const out = await captureFitOgSafe(
      row.name_key,
      hash,
      snap.body,
      snap.gold ?? row.last_gold,
      snap.played_seconds ?? row.last_played_seconds,
    )
    if (out?.path || out?.bytes) made += 1
    else failed += 1
  }
  return { ok: true, made, skipped, failed, ms: Date.now() - started }
}
