export function useWikiAccess() {
  const { user, profile } = useAuth()
  const { data: settings } = useAsyncData('site-settings', () => $fetch('/api/settings').catch(() => ({ open_edits: true })))

  const isAdmin = computed(() => profile.value?.role === 'admin')
  const confirmed = computed(() => Boolean(user.value?.email_confirmed_at || user.value?.confirmed_at))
  const canEdit = computed(() => Boolean(user.value && (isAdmin.value || confirmed.value)))

  return { isAdmin, canEdit, confirmed, settings }
}
