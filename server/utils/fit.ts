import { ATTR_PANEL, GEAR_SLOTS, HOTBAR_SLOTS, parseAvatarClass, qualityClass, WIKI_ORIGIN } from '#shared/fit'
import { wikiHref } from '#shared/wiki'
import catalogJson from '../data/fit-catalog.json'
import iconCaseJson from '../data/fit-icon-case.json'

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
  named?: Record<string, Record<string, number>>
  wiki?: string | null
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

const SKILL_FIXUPS: Record<string, CatalogSkill> = {
  'skills.generic.SummonSnowMan': {
    label: 'Build Snowman',
    description: 'You build a magical Snowman to help you in a fight. Ice skills keep him from melting.',
    icon: 'SummonSnowman_On',
    cooldown: 60,
    mana: 10.25,
    maxLevel: null,
    values: {},
    named: {},
    wiki: '/wiki/Build_Snowman',
  },
}

export function loadFitCatalog(): FitCatalog {
  const catalog = catalogJson as FitCatalog
  for (const [key, row] of Object.entries(SKILL_FIXUPS)) {
    const cur = catalog.skills[key]
    if (!cur?.icon) catalog.skills[key] = { ...row, ...cur }
  }
  return catalog
}

function lookupItem(catalog: FitCatalog, def: string): CatalogItem | null {
  const raw = String(def || '')
  if (!raw) return null
  const stripped = raw.replace(/^items\.pal\./i, '').replace(/^items\./i, '')
  if (catalog.items[raw]) return catalog.items[raw]
  if (catalog.items[stripped]) return catalog.items[stripped]
  const parts = stripped.split('.').filter(Boolean)
  if (parts.length >= 2) {
    const two = parts.slice(-2).join('.')
    if (catalog.items[two]) return catalog.items[two]
  }
  return null
}

function lookupSkill(catalog: FitCatalog, def: string): CatalogSkill | null {
  const raw = String(def || '')
  const short = raw.split('.').pop() || ''
  const direct = catalog.skills[raw] || catalog.skills['skills.generic.' + short]
  if (direct?.label || direct?.icon) return direct
  const lower = short.toLowerCase()
  for (const [key, row] of Object.entries(catalog.skills)) {
    if ((key.split('.').pop() || '').toLowerCase() === lower && (row.label || row.icon)) return row
  }
  return direct || null
}

function lookupMod(catalog: FitCatalog, def: string): CatalogMod | null {
  if (catalog.mods[def]) return catalog.mods[def]
  const trimmed = def.replace(/^items\.modpal\./i, '')
  if (catalog.mods[trimmed]) return catalog.mods[trimmed]
  const short = def.split('.').slice(-3).join('.')
  if (catalog.mods[short]) return catalog.mods[short]
  return null
}

const ICON_CASE = iconCaseJson as Record<string, string>

function iconUrl(stem: string | null | undefined): string | null {
  if (!stem) return null
  const actual = ICON_CASE[stem] || ICON_CASE[stem.toLowerCase()] || stem
  return `/fit/icons/${encodeURIComponent(actual)}.png`
}

function tableAtLevel(table: Record<string, number> | undefined, level: number): number | null {
  if (!table) return null
  if (table[String(level)] != null) return table[String(level)]
  const keys = Object.keys(table).map(Number).filter((n) => !Number.isNaN(n)).sort((a, b) => a - b)
  if (!keys.length) return null
  const max = keys[keys.length - 1]
  // Rank curves are small. Character-level knots (60/65/…/100) are not skill ranks.
  if (max > 25) return null
  if (keys.length === 1) return table[String(keys[0])]
  const closest = keys.reduce((best, n) => (Math.abs(n - level) < Math.abs(best - level) ? n : best), keys[0])
  return table[String(closest)]
}

function namedAtLevel(group: Record<string, number> | undefined, field: string, level: number): number | null {
  if (!group || group[field] == null) return null
  const inc = group[`${field}Inc`]
  if (inc == null) return group[field]
  return group[field] + (level - 1) * inc
}

function resolveSkillRef(ref: string, skill: CatalogSkill | null, level: number): number | null {
  if (!ref) return null
  if (/^-?(?:\d+\.\d+|\.\d+|\d+)$/.test(ref)) return Number(ref)
  const parts = ref.split('.')
  const field = parts.length > 1 ? parts.pop() as string : ''
  const name = parts.join('.')
  const tables = skill?.values || {}
  const named = skill?.named || {}

  if (name && field) {
    const fromTable = tableAtLevel(tables[name], level)
    if (fromTable != null) return fromTable
    const fromNamed = namedAtLevel(named[name], field, level)
    if (fromNamed != null) return fromNamed
    const fieldTable = tableAtLevel(tables[field], level)
    if (fieldTable != null) return fieldTable
  }

  if (!field) {
    const fromNamed = namedAtLevel(named[ref], 'Value', level)
      ?? namedAtLevel(named[ref], 'Duration', level)
      ?? namedAtLevel(Object.values(named).find((g) => g[ref] != null), ref, level)
    if (fromNamed != null) return fromNamed
    return tableAtLevel(tables[ref], level)
  }

  if (field.toLowerCase() === 'duration') {
    for (const key of [name, 'SpellModEffect', 'ModEffect', 'Duration']) {
      const hit = namedAtLevel(named[key], 'Duration', level) ?? tableAtLevel(tables[key], level) ?? tableAtLevel(tables.Duration, level)
      if (hit != null) return hit
    }
  }
  return null
}

function fillSkillText(text: string | null, skill: CatalogSkill | null, level: number): string | null {
  if (!text) return null
  return text.replace(
    /\[(-)?((?:[A-Za-z][\w]*\.)*[A-Za-z][\w]*)(?:\.([A-Za-z][\w]*))?(?:\*((?:\d+(?:\.\d+)?)|(?:(?:[A-Za-z][\w]*\.)*[A-Za-z][\w]*(?:\.[A-Za-z][\w]*)?)))?\]/g,
    (_all, neg: string | undefined, name: string, field?: string, mul?: string) => {
      const leftRef = field ? `${name}.${field}` : name
      const left = resolveSkillRef(leftRef, skill, level)
      if (left == null) return '—'
      let value = left
      if (mul) {
        const right = resolveSkillRef(mul, skill, level)
        if (right == null) return '—'
        value *= right
      }
      const shown = neg ? Math.abs(value) : value
      return formatNum(shown)
    },
  )
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
  twoHanded: boolean
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
  wiki: string | null
}

function buildItemName(base: string, resolved: { label: string | null, labelType: string | null }[]): string {
  const prefixes = resolved.filter((m) => m.labelType === 'PREFIX' && m.label).map((m) => m.label as string)
  const postfixes = resolved.filter((m) => m.labelType === 'POSTFIX' && m.label).map((m) => m.label as string)
  return [...prefixes, base, ...postfixes].join(' ').replace(/\s+/g, ' ').trim()
}

function isTwoHanded(def: string): boolean {
  const d = String(def || '').replace(/^items\.pal\./i, '')
  if (/(^|[._])1h/i.test(d)) return false
  return /(^|[._])2h/i.test(d) || /polearm/i.test(d)
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
    twoHanded: isTwoHanded(raw.def),
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
    wiki: wikiUrl(skill?.wiki),
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
