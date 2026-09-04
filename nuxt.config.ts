import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

function wikiRoutes(dir: string): string[] {
  const routes: string[] = []
  const walk = (current: string) => {
    for (const name of readdirSync(current)) {
      const full = join(current, name)
      if (statSync(full).isDirectory()) {
        walk(full)
        continue
      }
      if (!name.endsWith('.json')) continue
      try {
        const data = JSON.parse(readFileSync(full, 'utf8')) as { path?: string }
        if (!data.path) continue
        let path = data.path
        try {
          path = decodeURIComponent(data.path)
        }
        catch {
          // keep encoded
        }
        if (!/[()[\]?*]/.test(path)) routes.push(data.path)
      }
      catch {
        // skip broken generated files
      }
    }
  }
  try {
    walk(dir)
  }
  catch {
    return []
  }
  return routes
}

export default defineNuxtConfig({
  compatibilityDate: '2024-04-03',
  css: ['~/assets/css/wiki.css'],
  app: {
    head: {
      title: 'The Townstons',
      titleTemplate: '%s - Townstons',
      meta: [
        { name: 'description', content: 'Restored Dungeon Runners fansite wiki from thetownstons.com via the Wayback Machine.' },
      ],
      link: [
        { rel: 'icon', href: '/favicon.ico', sizes: '32x32' },
        { rel: 'icon', type: 'image/png', href: '/favicon.png', sizes: '32x32' },
        { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' },
      ],
    },
  },
  nitro: {
    prerender: {
      crawlLinks: false,
      failOnError: false,
      routes: ['/', '/all', '/api/wiki', '/api/pages', ...wikiRoutes('content/wiki')],
    },
  },
})
