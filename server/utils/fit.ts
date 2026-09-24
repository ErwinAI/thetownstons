import { ATTR_PANEL, GEAR_SLOTS, HOTBAR_SLOTS, parseAvatarClass, qualityClass, WIKI_ORIGIN } from '#shared/fit'
import { wikiHref } from '#shared/wiki'
import catalogJson from '../data/fit-catalog.json'

export type CatalogItem = {
  label: string
  icon: string | null
  quality: string | null
  damage: string | null
  speed: string | null
  defense: string | null
  wiki: string | null
  bakedMods: string[]
}

export type CatalogSkill = {
  label: string
  description: string | null
  icon: string | null
  cooldown: number | null
  mana: number | null
  maxLevel: number | null
  values: Record<string, Record<string, number>>
}

export type CatalogMod = {
  label: string | null
  labelType: string | null
  quality: string | null
  stats: string[]
}

export type FitCatalog = {
  items: Record<string, CatalogItem>
  skills: Record<string, CatalogSkill>
  mods: Record<string, CatalogMod>
}

export function loadFitCatalog(): FitCatalog {
  return catalogJson as FitCatalog
}

function lookupItem(catalog: FitCatalog, def: string): CatalogItem | null {
  if (catalog.items[def]) return catalog.items[def]
  const short = def.split('.').pop() || ''
  for (const [key, row] of Object.entries(catalog.items)) {
    if (key === short || key.endsWith('.' + short)) return row
  }
  return null
}

function lookupSkill(catalog: FitCatalog, def: string): CatalogSkill | null {
  return catalog.skills[def] || catalog.skills['skills.generic.' + (def.split('.').pop() || '')] || null
}

function lookupMod(catalog: FitCatalog, def: string): CatalogMod | null {
  if (catalog.mods[def]) return catalog.mods[def]
  const trimmed = def.replace(/^items\.modpal\./i, '')
  if (catalog.mods[trimmed]) return catalog.mods[trimmed]
  const short = def.split('.').slice(-3).join('.')
  if (catalog.mods[short]) return catalog.mods[short]
  return null
}

function iconUrl(stem: string | null | undefined): string | null {
  if (!stem) return null
  return `/fit/icons/${encodeURIComponent(stem)}.png`
}

function fillSkillText(text: string | null, skill: CatalogSkill | null, level: number): string | null {
  if (!text) return null
  return text.replace(/\[([A-Za-z0-9_]+)(?:\.([A-Za-z0-9_*]+))?\]/g, (all, name: string, field?: string) => {
    const tables = skill?.values || {}
    const kind = (field || '').toLowerCase()
    if (kind === 'duration' || name.toLowerCase().includes('duration')) {
      const table = tables.Duration || tables[name]
      if (table) {
        const exact = table[String(level)] ?? table['1']
        if (exact != null) return formatNum(exact)
      }
    }
    const table = tables[name] || tables.Value || tables[Object.keys(tables).find((k) => k !== 'Duration') || '']
    if (!table) return all
    const exact = table[String(level)]
    if (exact != null) return formatNum(exact)
    const keys = Object.keys(table).map(Number).filter((n) => !Number.isNaN(n)).sort((a, b) => a - b)
    if (!keys.length) return all
    const closest = keys.reduce((best, n) => (Math.abs(n - level) < Math.abs(best - level) ? n : best), keys[0])
    return formatNum(table[String(closest)])
  })
}

function formatNum(value: number): string {
  if (Number.isInteger(value)) return String(value)
  return String(Math.round(value * 100) / 100)
}

function cleanText(text: string): string {
  return text
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\t+/g, '')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\n{2,}/g, '\n')
    .trim()
}

function wikiUrl(path: string | null | undefined): string | null {
  if (!path) return null
  const href = wikiHref(path)
  return `${WIKI_ORIGIN}${href}`
}

type ApiMod = { def: string, level: number }
type ApiItem = { slot: number, def: string, level: number, mods: ApiMod[] }
type ApiSkill = { slot: number, def: string, level: number }

export type FitItemView = {
  slot: number
  slotKey: string
  slotLabel: string
  def: string
  level: number
  name: string
  quality: string | null
  qualityClass: string
  icon: string | null
  wiki: string | null
  lines: string[]
}

export type FitSkillView = {
  slot: number
  key: string
  def: string
  level: number
  name: string
  icon: string | null
  description: string | null
  cooldown: number | null
  mana: number | null
  maxLevel: number | null
}

function buildItemName(base: string, resolved: { label: string | null, labelType: string | null }[]): string {
  const prefixes = resolved.filter((m) => m.labelType === 'PREFIX' && m.label).map((m) => m.label as string)
  const postfixes = resolved.filter((m) => m.labelType === 'POSTFIX' && m.label).map((m) => m.label as string)
  return [...prefixes, base, ...postfixes].join(' ').replace(/\s+/g, ' ').trim()
}

function enrichItem(catalog: FitCatalog, raw: ApiItem): FitItemView {
  const item = lookupItem(catalog, raw.def)
  const slotMeta = GEAR_SLOTS.find((s) => s.id === raw.slot)
  const modDefs = (raw.mods?.length ? raw.mods.map((m) => m.def) : item?.bakedMods) || []
  const resolved = modDefs.map((def) => lookupMod(catalog, def)).filter(Boolean) as CatalogMod[]
  const base = item?.label || raw.def.split('.').pop() || 'Item'
  const name = buildItemName(base, resolved)
  const lines: string[] = [`Item level ${raw.level}`]
  if (item?.damage) lines.push(`Damage ${item.damage}`)
  if (item?.speed) lines.push(`Speed ${item.speed}`)
  if (item?.defense) lines.push(`Defense ${item.defense}`)
  for (const mod of resolved) {
    if (mod.label && mod.labelType && mod.labelType !== 'NONE' && (mod.labelType === 'PREFIX' || mod.labelType === 'POSTFIX')) {
      // name already includes these
    }
    else if (mod.label && mod.labelType === 'NONE') {
      // skip internal
    }
    for (const stat of mod.stats || []) {
      if (!lines.includes(stat)) lines.push(stat)
    }
  }
  const quality = item?.quality || resolved.find((m) => m.quality)?.quality || null
  return {
    slot: raw.slot,
    slotKey: slotMeta?.key || `slot${raw.slot}`,
    slotLabel: slotMeta?.label || `Slot ${raw.slot}`,
    def: raw.def,
    level: raw.level,
    name,
    quality,
    qualityClass: qualityClass(quality),
    icon: iconUrl(item?.icon),
    wiki: wikiUrl(item?.wiki),
    lines,
  }
}

function enrichSkill(catalog: FitCatalog, raw: ApiSkill): FitSkillView {
  const skill = lookupSkill(catalog, raw.def)
  const meta = HOTBAR_SLOTS.find((s) => s.id === raw.slot)
  return {
    slot: raw.slot,
    key: meta?.key || String(raw.slot),
    def: raw.def,
    level: raw.level,
    name: skill?.label || raw.def.split('.').pop() || 'Skill',
    icon: iconUrl(skill?.icon),
    description: skill?.description
      ? cleanText(fillSkillText(skill.description, skill, raw.level) || '')
      : null,
    cooldown: skill?.cooldown ?? null,
    mana: skill?.mana ?? null,
    maxLevel: skill?.maxLevel ?? null,
  }
}

export function presentCharacter(raw: Record<string, unknown>) {
  const catalog = loadFitCatalog()
  const avatar = parseAvatarClass(String(raw.class || ''))
  const spent = (raw.spent_attributes || {}) as Record<string, number>
  const equipment = Array.isArray(raw.equipment) ? raw.equipment as ApiItem[] : []
  const skills = Array.isArray(raw.equipped_skills) ? raw.equipped_skills as ApiSkill[] : []
  const gear = equipment.map((row) => enrichItem(catalog, row))
  const bySlot: Record<number, FitItemView> = {}
  for (const item of gear) bySlot[item.slot] = item
  const tray = skills.map((row) => enrichSkill(catalog, row))
  const bySkillSlot: Record<number, FitSkillView> = {}
  for (const skill of tray) bySkillSlot[skill.slot] = skill
  return {
    name: String(raw.name || ''),
    level: Number(raw.level || 0),
    classDef: String(raw.class || ''),
    classLabel: avatar.label,
    role: avatar.role,
    gender: avatar.gender,
    appearance: raw.appearance || null,
    attributes: ATTR_PANEL.map((row) => ({
      key: row.key,
      label: row.label,
      value: Number(spent[row.key] || 0),
    })),
    gear,
    bySlot,
    tray,
    bySkillSlot,
    slots: GEAR_SLOTS,
    hotbar: HOTBAR_SLOTS,
  }
}
