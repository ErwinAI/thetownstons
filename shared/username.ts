export function usernameError(raw: string): string | null {
  const name = raw.trim()
  if (name.length < 3) return 'Username must be at least 3 characters'
  if (name.length > 24) return 'Username must be at most 24 characters'
  if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(name)) return 'Start with a letter. Letters, numbers, underscore only.'
  return null
}

export function titleToSlug(title: string): string {
  return title.replace(/\s+/g, '_').replace(/^\/+|\/+$/g, '').trim()
}
