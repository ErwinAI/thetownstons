export default defineNuxtConfig({
  compatibilityDate: '2024-04-03',
  css: ['~/assets/css/wiki.css'],
  runtimeConfig: {
    supabaseServiceRoleKey: '',
    aiGatewayApiKey: '',
    fitCronBatch: 20,
    public: {
      supabaseUrl: '',
      supabaseAnonKey: '',
      siteUrl: 'https://www.thetownstons.com',
      fitSiteUrl: 'https://fit.thetownstons.com',
    },
  },
  app: {
    head: {
      title: 'The Townstons',
      titleTemplate: '%s - Townstons',
      meta: [
        { name: 'description', content: 'The Townstons — a Dungeon Runners fansite wiki. Live again, and open to edit.' },
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
      routes: ['/'],
    },
    vercel: {
      functions: {
        maxDuration: 60,
      },
      config: {
        crons: [
          { path: '/api/fit/cron', schedule: '27 * * * *' },
        ],
      },
    },
  },
  vite: {
    server: {
      allowedHosts: ['fit.thetownstons.com', 'fit.localhost', 'dungeonrunner.fit', '.dungeonrunner.fit'],
    },
  },
})
