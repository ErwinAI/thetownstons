import TurndownService from 'turndown'
import { gfm } from 'turndown-plugin-gfm'

const QUEST_LABELS: { label: string, key: string }[] = [
  { label: 'Quest Giver', key: 'giver' },
  { label: 'Quest Type', key: 'type' },
  { label: 'Quest Description', key: 'description' },
  { label: 'Quest Reward', key: 'reward' },
  { label: 'Return to', key: 'return' },
  { label: 'Repeatable', key: 'repeatable' },
  { label: 'Following Quest', key: 'following' },
  { label: 'Zone', key: 'zone' },
]

const turndown = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
  emDelimiter: '*',
})
turndown.use(gfm)
turndown.addRule('wikiLink', {
  filter: (node) => node.nodeName === 'A' && /^\/wiki\//.test(node.getAttribute('href') || ''),
  replacement: (content, node) => {
    const href = (node as HTMLElement).getAttribute('href') || ''
    return `[${content}](${href})`
  },
})

function pipeSafe(value: string): string {
  return value.replace(/\s+/g, ' ').replace(/\|/g, '/').replace(/\}\}/g, '} }').trim()
}

function decodeEntities(value: string): string {
  return value
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&#x27;/gi, "'")
    .replace(/&#(\d+);/g, (_all, n) => String.fromCharCode(Number(n)))
}

function stripTags(value: string): string {
  return decodeEntities(value.replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim()
}

function labelKey(label: string): string {
  return label
    .replace(/:$/, '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')
}

function findMatchingTable(html: string, from: number): { start: number, end: number, open: string } | null {
  const openRe = /<table\b[^>]*>/i
  const slice = html.slice(from)
  const open = slice.match(openRe)
  if (!open || open.index == null) return null
  const start = from + open.index
  let depth = 1
  let i = start + open[0].length
  const lower = html.toLowerCase()
  while (depth && i < html.length) {
    const nextOpen = lower.indexOf('<table', i)
    const nextClose = lower.indexOf('</table>', i)
    if (nextClose === -1) return null
    if (nextOpen !== -1 && nextOpen < nextClose) {
      depth++
      i = nextOpen + 6
    }
    else {
      depth--
      i = nextClose + 8
      if (!depth) return { start, end: i, open: open[0] }
    }
  }
  return null
}

function isInfoboxOpen(open: string): boolean {
  const tag = open.toLowerCase()
  if (/\binfobox\b/.test(tag)) return true
  if (/align\s*=\s*["']?right/.test(tag)) return true
  if (/width:\s*25%/.test(tag)) return true
  if (/#9999ff/.test(tag)) return true
  return false
}

function parseInfobox(tableHtml: string): string {
  const args: string[] = []
  const img = tableHtml.match(/<img[^>]+src=["']([^"']+)["']/i)
  const rows = [...tableHtml.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)]
  for (const row of rows) {
    const cells = [...row[1].matchAll(/<t[dh]\b[^>]*>([\s\S]*?)<\/t[dh]>/gi)].map((cell) => cell[1])
    if (!cells.length) continue
    if (cells.length === 1) {
      if (/<img/i.test(cells[0])) continue
      const title = stripTags(cells[0])
      if (title && title !== '—' && !args.some((arg) => arg.startsWith('title='))) {
        args.unshift(`title=${pipeSafe(title)}`)
      }
      continue
    }
    const label = stripTags(cells[0]).replace(/:$/, '')
    const value = pipeSafe(turndown.turndown(cells[1]))
    const key = labelKey(label)
    if (label && value && key) args.push(`${key}=${value}`)
  }
  if (img) args.splice(args[0]?.startsWith('title=') ? 1 : 0, 0, `image=${img[1]}`)
  if (!args.length) return ''
  return `{{infobox|${args.join('|')}}}`
}

function extractInfoboxes(html: string): { boxes: string[], rest: string } {
  const boxes: string[] = []
  let rest = html
  let from = 0
  while (from < rest.length) {
    const found = findMatchingTable(rest, from)
    if (!found) break
    if (!isInfoboxOpen(found.open)) {
      from = found.end
      continue
    }
    const tpl = parseInfobox(rest.slice(found.start, found.end))
    if (tpl) boxes.push(tpl)
    rest = rest.slice(0, found.start) + rest.slice(found.end)
    from = found.start
  }
  return { boxes, rest }
}

function extractThumbs(html: string): { thumbs: string[], rest: string } {
  const thumbs: string[] = []
  const rest = html.replace(/<div class="thumb[^"]*"[\s\S]*?<\/div>\s*<\/div>/gi, (block) => {
    const src = block.match(/<img[^>]+src=["']([^"']+)["']/i)?.[1]
    const caption = stripTags(block.match(/thumbcaption[^>]*>([\s\S]*?)<\/div>/i)?.[1] || '')
    const align = /tleft|float:\s*left/i.test(block) ? 'left' : 'right'
    if (!src) return ''
    thumbs.push(`{{thumb|src=${src}|caption=${pipeSafe(caption)}|align=${align}}}`)
    return ''
  })
  return { thumbs, rest }
}

export function htmlToWikiMarkdown(html: string): string {
  let rest = (html || '')
    .replace(/<div id="mw-pages">[\s\S]*?<\/div>/gi, '')
    .replace(/<div id="mw-subcategories">[\s\S]*?<\/div>/gi, '')
    .replace(/<div class="catlinks">[\s\S]*?<\/div>/gi, '')
    .replace(/<table\b[^>]*\bid="toc"[^>]*>[\s\S]*?<\/table>/gi, '')
    .replace(/<table\b[^>]*\bclass="toc"[^>]*>[\s\S]*?<\/table>/gi, '')
    .replace(/<div class="visualClear"><\/div>/gi, '')

  const quest: Record<string, string> = {}
  for (const field of QUEST_LABELS) {
    const re = new RegExp(`<p>\\s*<b>\\s*${field.label}:\\s*</b>\\s*([\\s\\S]*?)</p>`, 'i')
    const match = rest.match(re)
    if (!match) continue
    quest[field.key] = pipeSafe(turndown.turndown(match[1]))
    rest = rest.replace(re, '')
  }

  const boxed = extractInfoboxes(rest)
  const thumbs = extractThumbs(boxed.rest)
  const body = turndown.turndown(thumbs.rest)
    .replace(/\\([-+])/g, '$1')
    .replace(/^(?:[ \t]*&nbsp;[ \t]*\n)+/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

  const parts: string[] = []
  if (Object.keys(quest).length) {
    const args = QUEST_LABELS
      .filter((field) => quest[field.key])
      .map((field) => `${field.key}=${quest[field.key]}`)
      .join('|')
    parts.push(`{{quest|${args}}}`)
  }
  parts.push(...boxed.boxes, ...thumbs.thumbs)
  if (body) parts.push(body)
  return parts.join('\n\n').trim()
}
