import type { SupabaseClient } from '@supabase/supabase-js'

declare module '#app' {
  interface NuxtApp {
    $supabase?: SupabaseClient
  }
}

declare module 'turndown-plugin-gfm' {
  import type { Plugin } from 'turndown'
  export const gfm: Plugin
  export const tables: Plugin
}
