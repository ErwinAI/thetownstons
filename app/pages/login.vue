<script setup lang="ts">
const route = useRoute()
const fromKarl = computed(() => route.query.from === 'karl')
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
    await navigateTo(fromKarl.value ? '/karl' : '/')
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
    <table v-if="fromKarl" class="infobox wiki-karl-note">
      <tbody>
        <tr><th>KarlAI</th></tr>
        <tr><td>KarlAI needs an account and a confirmed email before he will answer. Log in, then ask again from any page.</td></tr>
      </tbody>
    </table>
    <p v-if="!config.public.supabaseUrl">Auth is not configured.</p>
    <form v-else class="wiki-form" @submit.prevent="submit">
      <p><label>Email<br><input v-model="email" type="email" required autocomplete="email"></label></p>
      <p><label>Password<br><input v-model="password" type="password" required autocomplete="current-password"></label></p>
      <p v-if="error" class="wiki-form-error">{{ error }}</p>
      <p><button type="submit" :disabled="pending">{{ pending ? 'Signing in…' : 'Log in' }}</button></p>
      <p>No account? <NuxtLink :to="fromKarl ? '/signup?from=karl' : '/signup'">Sign up</NuxtLink></p>
    </form>
  </article>
</template>
