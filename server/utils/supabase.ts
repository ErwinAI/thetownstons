import { createClient, type SupabaseClient, type User } from '@supabase/supabase-js'

function publicConfig() {
  const config = useRuntimeConfig()
  return {
    url: String(config.public.supabaseUrl || ''),
    anonKey: String(config.public.supabaseAnonKey || ''),
    serviceKey: String(config.supabaseServiceRoleKey || ''),
  }
}

export function supabaseConfigured(): boolean {
  const { url, anonKey } = publicConfig()
  return Boolean(url && anonKey)
}

export function serviceClient(): SupabaseClient | null {
  const { url, serviceKey, anonKey } = publicConfig()
  const key = serviceKey || anonKey
  if (!url || !key) return null
  return createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  })
}

export function anonClient(): SupabaseClient | null {
  const { url, anonKey } = publicConfig()
  if (!url || !anonKey) return null
  return createClient(url, anonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  })
}

export async function userFromRequest(event: Parameters<typeof getHeader>[0]): Promise<User | null> {
  const header = getHeader(event, 'authorization') || ''
  const token = header.startsWith('Bearer ') ? header.slice(7).trim() : ''
  if (!token) return null
  const client = anonClient()
  if (!client) return null
  const { data, error } = await client.auth.getUser(token)
  if (error || !data.user) return null
  return data.user
}
