import { marked } from 'marked'
import { foldCategoryName, sanitizeWikiHtml } from './wiki'

const CATEGORY_WIKI = /\[\[Category:([^\]|]+)(?:\|[^\]]*)?\]\]/gi
const CATEGORY_TPL = /\{\{\s*category\s*\|\s*([^}|]+)\s*\}\}/gi

export function extractWikiCategories(source: string): { text: string, categories: string[] } {
  const categories: string[] = []
  const text = (source || '')
    .replace(CATEGORY_WIKI, (_all, name: string) => {
      const clean = foldCategoryName(name)
      if (clean) categories.push(clean)
      return ''
    })
    .replace(CATEGORY_TPL, (_all, name: string) => {
      const clean = foldCategoryName(name)
      if (clean) categories.push(clean)
      return ''
    })
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
  return { text, categories }
}

marked.setOptions({ gfm: true, breaks: true })

const TEMPLATE = /\{\{(\w+)(\|[\s\S]*?)?\}\}/g

const QUEST_FIELDS: { key: string, label: string }[] = [
  { key: 'giver', label: 'Quest Giver' },
  { key: 'type', label: 'Quest Type' },
  { key: 'description', label: 'Quest Description' },
  { key: 'reward', label: 'Quest Reward' },
  { key: 'return', label: 'Return to' },
  { key: 'repeatable', label: 'Repeatable' },
  { key: 'following', label: 'Following Quest' },
  { key: 'zone', label: 'Zone' },
]

function parseArgs(raw: string): Record<string, string> {
  const args: Record<string, string> = {}
  if (!raw) return args
  for (const part of raw.split('|')) {
    if (!part) continue
    const eq = part.indexOf('=')
    if (eq === -1) continue
    args[part.slice(0, eq).trim().toLowerCase()] = part.slice(eq + 1).trim()
  }
  return args
}

function inline(value: string): string {
  if (!value) return ''
  return String(marked.parseInline(value, { async: false }))
}

function renderQuest(args: Record<string, string>): string {
  const rows = QUEST_FIELDS
    .filter((field) => args[field.key])
    .map((field) => `<p><b>${field.label}:</b> ${inline(args[field.key])}</p>`)
  return rows.join('\n')
}

function renderThumb(args: Record<string, string>): string {
  const src = args.src || args.image || ''
  const caption = args.caption || args.title || ''
  const align = (args.align || 'right').toLowerCase() === 'left' ? 'tleft' : 'tright'
  if (!src) return ''
  const alt = caption.replace(/<[^>]+>/g, '')
  return `<div class="thumb ${align}"><a class="image" href="${src}"><img src="${src}" alt="${alt}"></a>${caption ? `<div class="thumbcaption">${inline(caption)}</div>` : ''}</div>`
}

function renderInfobox(args: Record<string, string>): string {
  const title = args.title || args.name || ''
  const image = args.image || args.src || ''
  const skip = new Set(['title', 'name', 'image', 'src'])
  const rows = Object.entries(args)
    .filter(([key, value]) => value && !skip.has(key))
    .map(([key, value]) => {
      const label = key.replace(/_/g, ' ').replace(/\b\w/g, (ch) => ch.toUpperCase())
      return `<tr><td style="width:50%;" valign="top"><b>${label}: </b></td><td style="width:50%;" valign="top">${inline(value)}</td></tr>`
    })
    .join('')
  const head = title
    ? `<tr><td colspan="2" style="text-align:center; background:#9999FF; font-size:150%;">${inline(title)}</td></tr>`
    : ''
  const pic = image
    ? `<tr><td colspan="2" style="text-align:center;"><a class="image" href="${image}"><img src="${image}" alt=""></a></td></tr>`
    : ''
  return `<table class="infobox" align="right" cellpadding="2" cellspacing="0" style="text-align:left; background:rgb(240,240,240); border:1px solid black; width:25%;">${head}${pic}${rows}</table>`
}

function renderTemplate(name: string, args: Record<string, string>): string {
  if (name === 'quest') return renderQuest(args)
  if (name === 'thumb') return renderThumb(args)
  if (name === 'infobox') return renderInfobox(args)
  return ''
}

export function renderWikiMarkdown(source: string): string {
  const pulled = extractWikiCategories(source)
  const withTemplates = pulled.text.replace(TEMPLATE, (_all, name: string, raw = '') => {
    return renderTemplate(String(name).toLowerCase(), parseArgs(String(raw)))
  })
  const html = String(marked.parse(withTemplates, { async: false }))
  return sanitizeWikiHtml(html)
}
