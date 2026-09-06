export default defineNuxtPlugin(async () => {
  const config = useRuntimeConfig()
  const { refresh } = useAuth()
  if (!config.public.supabaseUrl || !config.public.supabaseAnonKey) {
    await refresh()
    return
  }
  await refresh()
  useSupabase().auth.onAuthStateChange(() => {
    refresh()
  })
})
