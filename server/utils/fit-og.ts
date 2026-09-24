import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { parse as parseOpenType } from 'opentype.js'
import { FIT_OG_VERSION, GEAR_SLOTS } from '#shared/fit'
import { formatGold, formatPlayed } from '#shared/fit-xp'
import { presentCharacter, type FitItemView } from './fit'
import { serviceClient } from './supabase'

export const OG_WIDTH = 1200
export const OG_HEIGHT = 630
export const OG_BUCKET = 'fit-og'
export const OG_VERSION = FIT_OG_VERSION

const EQUIP_SRC = { w: 365, h: 276 }
const STATS_SRC = { w: 367, h: 571 }

const SLOT_BOX: Record<string, { l: number, t: number, w: number, h: number }> = {
  weapon: { l: 0.079, t: 0.181, w: 0.170, h: 0.453 },
  helm: { l: 0.312, t: 0.192, w: 0.162, h: 0.221 },
  shield: { l: 0.534, t: 0.188, w: 0.164, h: 0.446 },
  shoulders: { l: 0.751, t: 0.181, w: 0.173, h: 0.228 },
  armor: { l: 0.310, t: 0.482, w: 0.164, h: 0.438 },
  ring1: { l: 0.742, t: 0.500, w: 0.082, h: 0.116 },
  ring2: { l: 0.836, t: 0.500, w: 0.082, h: 0.116 },
  gloves: { l: 0.077, t: 0.688, w: 0.173, h: 0.228 },
  boots: { l: 0.532, t: 0.692, w: 0.164, h: 0.221 },
  amulet: { l: 0.751, t: 0.685, w: 0.173, h: 0.232 },
}

const uiCache = new Map<string, Buffer>()
let bucketReady = false

export type FitOgView = {
  name: string
  subtitle?: string
  level: number
  classLabel: string
  attributes: { key: string, label: string, value: number | null }[]
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
      if (rel.startsWith('fit/ui/') || rel.startsWith('fit/fonts/')) uiCache.set(rel, buf)
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
    if (rel.startsWith('fit/ui/') || rel.startsWith('fit/fonts/')) uiCache.set(rel, buf)
    return buf
  }
  catch {
    return null
  }
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

type OgFont = ReturnType<typeof parseOpenType>
let ogFonts: { regular: OgFont, bold: OgFont } | null = null

function fontFromBuffer(buf: Buffer) {
  const copy = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength)
  return parseOpenType(copy)
}

async function readFontBytes(name: string): Promise<Buffer | null> {
  try {
    const raw = await useStorage('assets:fit-fonts').getItemRaw(name)
    if (raw) return Buffer.from(raw as ArrayBuffer)
  }
  catch {
    // public/ fallback
  }
  return readPublic(`fit/fonts/${name}`)
}

async function loadOgFonts() {
  if (ogFonts) return ogFonts
  const [regular, bold] = await Promise.all([
    readFontBytes('Inter-Regular.ttf'),
    readFontBytes('Inter-Bold.ttf'),
  ])
  if (!regular || !bold) throw new Error('Fit OG fonts missing')
  ogFonts = { regular: fontFromBuffer(regular), bold: fontFromBuffer(bold) }
  return ogFonts
}

function textPath(
  font: OgFont,
  text: string,
  x: number,
  y: number,
  size: number,
  fill: string,
  anchor: 'start' | 'middle' | 'end' = 'start',
) {
  const scale = size / (font.unitsPerEm || 1000)
  const glyphs = Array.from(text).map((ch) => font.charToGlyph(ch))
  const width = glyphs.reduce((sum, glyph) => sum + (glyph.advanceWidth || 0) * scale, 0)
  let cursor = x
  if (anchor === 'middle') cursor = x - width / 2
  if (anchor === 'end') cursor = x - width
  return glyphs.map((glyph) => {
    const path = glyph.getPath(cursor, y, size, {}, font)
    path.fill = fill
    const svg = path.toSVG(1)
    cursor += (glyph.advanceWidth || 0) * scale
    return svg
  }).join('')
}

export function isCurrentOg(
  row: { og_hash?: string | null, og_path?: string | null } | null | undefined,
  hash: string,
) {
  if (!row || !hash) return false
  return row.og_hash === hash && String(row.og_path || '').includes(`/v${OG_VERSION}/`)
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
    .resize({ width: innerW, height: innerH, fit: 'inside', kernel: 'lanczos3' })
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

  const originX = 72
  const originY = 22
  const footerH = 96
  const leftW = 560
  const nameplateW = 292
  const nameplateH = 96
  const nameplateX = originX + Math.round((leftW - nameplateW) / 2)
  const nameplateY = originY
  const equipW = leftW
  const equipH = Math.round(equipW * EQUIP_SRC.h / EQUIP_SRC.w)
  const equipX = originX
  const equipY = nameplateY + nameplateH + 8
  const statsH = OG_HEIGHT - originY - footerH
  const statsW = Math.round(statsH * STATS_SRC.w / STATS_SRC.h)
  const statsX = originX + leftW + 32
  const statsY = originY
  const bySlot = view.bySlot || {}
  const subtitle = view.subtitle ?? `Level ${view.level} ${view.classLabel}`
  const nameSize = view.name.length > 18 ? 22 : view.name.length > 13 ? 26 : 30
  const fonts = await loadOgFonts()

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

  const nameCard = await sharp(nameplate)
    .resize(nameplateW, nameplateH)
    .png()
    .toBuffer()

  const statsCard = await sharp(stats)
    .resize(statsW, statsH)
    .png()
    .toBuffer()

  const nameCx = nameplateX + Math.round(nameplateW / 2)
  const attrRows = view.attributes || []
  const attrTop = statsY + statsH * 0.112
  const attrH = statsH * 0.205
  const attrN = Math.max(attrRows.length, 1)
  const labelX = statsX + statsW * 0.14
  const valueX = statsX + statsW * 0.86
  const attrSvg = attrRows.map((row, i) => {
    const y = Math.round(attrTop + attrH * (i + 0.5) / attrN)
    const value = row.value == null ? '—' : String(row.value)
    return `${textPath(fonts.regular, row.label, labelX, y, 20, '#b9a078')}
      ${textPath(fonts.regular, value, valueX, y, 20, '#ffffff', 'end')}`
  }).join('')
  const metaY1 = Math.round(statsY + statsH * 0.405)
  const metaY2 = Math.round(statsY + statsH * 0.455)
  const overlay = Buffer.from(`<?xml version="1.0" encoding="UTF-8"?>
    <svg width="${OG_WIDTH}" height="${OG_HEIGHT}" viewBox="0 0 ${OG_WIDTH} ${OG_HEIGHT}" xmlns="http://www.w3.org/2000/svg">
      ${textPath(fonts.bold, view.name, nameCx, nameplateY + 50, nameSize, '#f3e6c4', 'middle')}
      ${textPath(fonts.regular, subtitle, nameCx, nameplateY + 70, 16, '#b9a078', 'middle')}
      ${textPath(fonts.bold, 'Attributes spent', statsX + statsW / 2, Math.round(statsY + statsH * 0.054), 18, '#d4b056', 'middle')}
      ${attrSvg}
      ${textPath(fonts.regular, 'Gold', labelX, metaY1, 20, '#b9a078')}
      ${textPath(fonts.regular, formatGold(view.gold), valueX, metaY1, 20, '#ffffff', 'end')}
      ${textPath(fonts.regular, 'Played', labelX, metaY2, 20, '#b9a078')}
      ${textPath(fonts.regular, formatPlayed(view.playedSeconds), valueX, metaY2, 20, '#ffffff', 'end')}
      ${textPath(fonts.regular, 'Check your own char!', OG_WIDTH - 36, OG_HEIGHT - 72, 18, '#c4a060', 'end')}
      ${textPath(fonts.bold, 'DungeonRunner.Fit', OG_WIDTH - 36, OG_HEIGHT - 40, 32, '#e8c56b', 'end')}
      ${textPath(fonts.bold, 'TheTownstons', OG_WIDTH - 36, OG_HEIGHT - 12, 24, '#f3e6c4', 'end')}
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
      { input: overlay, left: 0, top: 0 },
    ])
    .png()
    .toBuffer()
}

export async function renderDefaultFitOg() {
  return renderFitOgPng({
    name: 'Fit',
    subtitle: 'Look someone up',
    level: 0,
    classLabel: '',
    attributes: [
      { key: 'str', label: 'Strength', value: null },
      { key: 'agi', label: 'Agility', value: null },
      { key: 'end', label: 'Endurance', value: null },
      { key: 'pow', label: 'Power', value: null },
    ],
    bySlot: {},
    gold: null,
    playedSeconds: null,
  })
}

export function ogObjectPath(nameKey: string, hash: string) {
  return `chars/${nameKey}/v${OG_VERSION}/${hash}.png`
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
    .select('name_key, display_name, payload_hash, og_hash, og_path, last_gold, last_played_seconds, last_fetched_at')
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
    og_path?: string | null
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
    if (isCurrentOg(row, hash)) {
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
