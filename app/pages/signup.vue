<script setup lang="ts">
import { usernameError } from '#shared/username'

const username = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const notice = ref('')
const pending = ref(false)
const { refresh } = useAuth()
const config = useRuntimeConfig()

async function submit() {
  error.value = ''
  notice.value = ''
  const name = username.value.trim()
  const bad = usernameError(name)
  if (bad) {
    error.value = bad
    return
  }
  pending.value = true
  try {
    const { data: taken } = await useSupabase().from('users').select('id').ilike('username', name).maybeSingle()
    if (taken?.id) throw new Error('That username is taken')
    const { data, error: authError } = await useSupabase().auth.signUp({
      email: email.value.trim(),
      password: password.value,
      options: {
        emailRedirectTo: config.public.siteUrl,
        data: { username: name },
      },
    })
    if (authError) throw authError
    await refresh()
    if (data.session) {
      await navigateTo('/')
      return
    }
    notice.value = 'Check your email to confirm the account, then log in.'
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : 'Sign up failed'
  }
  finally {
    pending.value = false
  }
}

useHead({ title: 'Sign up' })
</script>

<template>
  <article>
    <h1 class="firstHeading">Sign up</h1>
    <div id="siteSub">From Townstons</div>
    <p>Pick a username. That is what shows on edits, not your email.</p>
    <form class="wiki-form" @submit.prevent="submit">
      <p><label>Username<br><input v-model="username" required minlength="3" maxlength="24" autocomplete="username"></label></p>
      <p><label>Email<br><input v-model="email" type="email" required autocomplete="email"></label></p>
      <p><label>Password<br><input v-model="password" type="password" required minlength="6" autocomplete="new-password"></label></p>
      <p v-if="error" class="wiki-form-error">{{ error }}</p>
      <p v-if="notice">{{ notice }}</p>
      <p><button type="submit" :disabled="pending">{{ pending ? 'Creating…' : 'Create account' }}</button></p>
      <p>Already have one? <NuxtLink to="/login">Log in</NuxtLink></p>
    </form>
  </article>
</template>
