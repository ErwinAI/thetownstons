import type { User } from '@supabase/supabase-js'
import { serviceClient } from './supabase'

export function isEmailConfirmed(user: User): boolean {
  const extra = user as User & { confirmed_at?: string }
  return Boolean(user.email_confirmed_at || extra.confirmed_at)
}

export function assertEmailConfirmed(user: User) {
  if (isEmailConfirmed(user)) return
  throw createError({ statusCode: 403, statusMessage: 'Confirm your email first' })
}

export async function userProfile(userId: string) {
  const db = serviceClient()
  if (!db) return null
  const { data } = await db.from('users').select('id, username, role').eq('id', userId).maybeSingle()
  return data as { id: string, username: string | null, role: string | null } | null
}

export async function openEditsEnabled() {
  const db = serviceClient()
  if (!db) return false
  const { data } = await db.from('site_settings').select('value').eq('key', 'open_edits').maybeSingle()
  return data?.value === true || data?.value === 'true'
}

export async function assertCanEdit(userId: string, locked?: boolean) {
  const profile = await userProfile(userId)
  if (!profile) {
    throw createError({ statusCode: 403, statusMessage: 'No profile' })
  }
  if (profile.role === 'admin') return profile
  if (locked) {
    throw createError({ statusCode: 403, statusMessage: 'This page is locked' })
  }
  return profile
}

export async function assertAdmin(userId: string) {
  const profile = await userProfile(userId)
  if (profile?.role !== 'admin') {
    throw createError({ statusCode: 403, statusMessage: 'Admins only' })
  }
  return profile
}

export async function setOpenEdits(on: boolean) {
  const db = serviceClient()
  if (!db) throw createError({ statusCode: 503, statusMessage: 'Wiki store is not configured' })
  const { error } = await db.from('site_settings').upsert({ key: 'open_edits', value: on })
  if (error) throw createError({ statusCode: 500, statusMessage: error.message })
}
