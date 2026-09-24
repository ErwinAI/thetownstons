export const FIT_HOSTS = [
  /^fit\./i,
  /(^|\.)dungeonrunner\.fit$/i,
]

export const WIKI_ORIGIN = 'https://www.thetownstons.com'
export const FIT_ORIGIN = 'https://fit.thetownstons.com'

export function hostName(host: string): string {
  return String(host || '').split(':')[0].trim().toLowerCase()
}

export function isFitHost(host: string): boolean {
  const name = hostName(host)
  if (!name) return false
  if (name === 'fit.localhost' || name.endsWith('.fit.localhost')) return true
  return FIT_HOSTS.some((re) => re.test(name))
}

export function isFitPassthrough(path: string): boolean {
  return /^\/(_nuxt|_ipx|__nuxt|api\/|images\/|fit\/|favicon|apple-touch|robots|sitemap|_vercel)/i.test(path)
}

export const GEAR_SLOTS = [
  { id: 10, key: 'weapon', label: 'Weapon' },
  { id: 11, key: 'shield', label: 'Off-hand' },
  { id: 5, key: 'helm', label: 'Helm' },
  { id: 1, key: 'amulet', label: 'Amulet' },
  { id: 6, key: 'armor', label: 'Armor' },
  { id: 2, key: 'gloves', label: 'Gloves' },
  { id: 8, key: 'shoulders', label: 'Shoulders' },
  { id: 3, key: 'ring1', label: 'Ring' },
  { id: 4, key: 'ring2', label: 'Ring' },
  { id: 7, key: 'boots', label: 'Boots' },
] as const

export const HOTBAR_SLOTS = [
  { id: 100, key: 'L' },
  { id: 101, key: '1' },
  { id: 102, key: '2' },
  { id: 103, key: '3' },
  { id: 104, key: '4' },
  { id: 105, key: '5' },
  { id: 106, key: '6' },
  { id: 107, key: '7' },
  { id: 108, key: '8' },
  { id: 109, key: 'R' },
] as const

export const ATTR_PANEL = [
  { key: 'strength', label: 'Strength' },
  { key: 'agility', label: 'Agility' },
  { key: 'toughness', label: 'Endurance' },
  { key: 'power', label: 'Power' },
] as const

const CLASS_NAME: Record<string, { role: string, gender: string }> = {
  FighterFemale: { role: 'Fighter', gender: 'Female' },
  FighterMale: { role: 'Fighter', gender: 'Male' },
  RangerFemale: { role: 'Ranger', gender: 'Female' },
  RangerMale: { role: 'Ranger', gender: 'Male' },
  WarlockFemale: { role: 'Mage', gender: 'Female' },
  WarlockMale: { role: 'Mage', gender: 'Male' },
}

export function parseAvatarClass(raw: string): { role: string, gender: string, label: string } {
  const short = String(raw || '').split('.').pop() || ''
  const hit = CLASS_NAME[short]
  if (hit) return { ...hit, label: `${hit.gender} ${hit.role}` }
  const role = short.replace(/Female|Male/g, '') || 'Adventurer'
  const gender = /Female/i.test(short) ? 'Female' : /Male/i.test(short) ? 'Male' : ''
  const pretty = role === 'Warlock' ? 'Mage' : role
  return { role: pretty, gender, label: [gender, pretty].filter(Boolean).join(' ') || pretty }
}

export function qualityClass(quality: string | null | undefined): string {
  const q = String(quality || '').toLowerCase()
  if (q.includes('mythic')) return 'q-mythic'
  if (q.includes('unique')) return 'q-unique'
  if (q.includes('rare')) return 'q-rare'
  if (q.includes('magic')) return 'q-magic'
  if (q.includes('superior')) return 'q-superior'
  if (q.includes('quest')) return 'q-quest'
  return 'q-normal'
}

export const CHAR_NAME_RE = /^[A-Za-z0-9_ ]{1,64}$/

export function normalizeCharName(raw: string): string | null {
  const name = String(raw || '').replace(/\+/g, ' ').replace(/\s+/g, ' ').trim()
  if (!CHAR_NAME_RE.test(name)) return null
  return name
}
