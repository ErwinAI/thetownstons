<script setup lang="ts">
const email = ref('')
const password = ref('')
const error = ref('')
const pending = ref(false)
const { refresh } = useAuth()
const config = useRuntimeConfig()

async function submit() {
  error.value = ''
  pending.value = true
  try {
    const { error: authError } = await useSupabase().auth.signInWithPassword({
      email: email.value.trim(),
      password: password.value,
    })
    if (authError) throw authError
    await refresh()
    await navigateTo('/')
  }
  catch (err) {
    error.value = err instanceof Error ? err.message : 'Sign in failed'
  }
  finally {
    pending.value = false
  }
}

useHead({ title: 'Log in' })
</script>

<template>
  <article>
    <h1 class="firstHeading">Log in</h1>
    <div id="siteSub">From Townstons</div>
    <p v-if="!config.public.supabaseUrl">Auth is not configured.</p>
    <form v-else class="wiki-form" @submit.prevent="submit">
      <p><label>Email<br><input v-model="email" type="email" required autocomplete="email"></label></p>
      <p><label>Password<br><input v-model="password" type="password" required autocomplete="current-password"></label></p>
      <p v-if="error" class="wiki-form-error">{{ error }}</p>
      <p><button type="submit" :disabled="pending">{{ pending ? 'Signing in…' : 'Log in' }}</button></p>
      <p>No account? <NuxtLink to="/signup">Sign up</NuxtLink></p>
    </form>
  </article>
</template>
