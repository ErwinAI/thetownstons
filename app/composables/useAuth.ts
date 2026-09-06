import type { User } from '@supabase/supabase-js'

export type WikiProfile = {
  username: string | null
  display_name: string | null
  role: string | null
}

export function useAuth() {
  const user = useState<User | null>('auth-user', () => null)
  const profile = useState<WikiProfile | null>('auth-profile', () => null)
  const ready = useState('auth-ready', () => false)
  const config = useRuntimeConfig()

  async function refresh() {
    if (!config.public.supabaseUrl || !config.public.supabaseAnonKey) {
      user.value = null
      profile.value = null
      ready.value = true
      return
    }
    const { data } = await useSupabase().auth.getSession()
    user.value = data.session?.user ?? null
    if (!user.value) {
      profile.value = null
      ready.value = true
      return
    }
    const { data: row } = await useSupabase()
      .from('users')
      .select('username, display_name, role')
      .eq('id', user.value.id)
      .maybeSingle()
    profile.value = row || {
      username: (user.value.user_metadata?.username as string) || null,
      display_name: null,
      role: null,
    }
    ready.value = true
  }

  async function token() {
    if (!config.public.supabaseUrl) return null
    const { data } = await useSupabase().auth.getSession()
    return data.session?.access_token ?? null
  }

  return { user, profile, ready, refresh, token }
}
