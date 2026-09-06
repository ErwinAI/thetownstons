import { createClient, type SupabaseClient } from '@supabase/supabase-js'

export function useSupabase(): SupabaseClient {
  const nuxt = useNuxtApp()
  if (nuxt.$supabase) return nuxt.$supabase as SupabaseClient

  const config = useRuntimeConfig()
  const client = createClient(
    String(config.public.supabaseUrl || 'https://unavailable.supabase.co'),
    String(config.public.supabaseAnonKey || 'public-anon-key'),
    {
      auth: {
        persistSession: import.meta.client,
        autoRefreshToken: import.meta.client,
        detectSessionInUrl: import.meta.client,
      },
    },
  )
  nuxt.$supabase = client
  return client
}
