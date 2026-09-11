<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, tokens } from '../api'

const route = useRoute()
const router = useRouter()

const mode = ref('login')
const username = ref('')
const password = ref('')
const error = ref('')
const notice = ref('')
const busy = ref(false)
const autoApprove = ref(false)

onMounted(async () => {
  try {
    const health = await api.health()
    autoApprove.value = !!health?.auth?.auto_approve
  } catch {
    // /health being unreachable is surfaced on the first real request instead.
  }
})

async function submit() {
  error.value = ''
  notice.value = ''
  busy.value = true
  try {
    if (mode.value === 'login') {
      const res = await api.login(username.value.trim(), password.value)
      tokens.setUser(res.access_token, res.username)
      router.push(route.query.next || '/chat')
    } else {
      const res = await api.register(username.value.trim(), password.value)
      if (res.access_token) {
        // Auto-approve is on: log straight in rather than showing a dead end.
        tokens.setUser(res.access_token, res.username)
        router.push('/chat')
      } else {
        notice.value = res.message
        mode.value = 'login'
      }
    }
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="wrap">
    <div class="panel card">
      <h1>Travel Steezy</h1>
      <p class="muted small intro">
        A travel assistant for long-term backpackers. Tell it where you are, what
        your budget is and how long you have, and it will weigh up where to go next
        on weather, visas, routes and cost.
      </p>

      <div class="tabs">
        <button :class="{ active: mode === 'login' }" class="ghost" @click="mode = 'login'">Log in</button>
        <button :class="{ active: mode === 'register' }" class="ghost" @click="mode = 'register'">Register</button>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
      <div v-if="notice" class="notice">{{ notice }}</div>

      <form @submit.prevent="submit">
        <div class="field">
          <label for="u">Username</label>
          <input id="u" v-model="username" autocomplete="username" required minlength="3" />
        </div>
        <div class="field">
          <label for="p">Password</label>
          <input
            id="p"
            v-model="password"
            type="password"
            :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
            required
            minlength="8"
          />
        </div>
        <button class="primary full" :disabled="busy" type="submit">
          {{ busy ? 'Working...' : mode === 'login' ? 'Log in' : 'Create account' }}
        </button>
      </form>

      <p v-if="mode === 'register' && !autoApprove" class="muted small foot">
        New accounts need admin approval before you can log in.
      </p>
      <p v-if="mode === 'register' && autoApprove" class="muted small foot">
        This deployment approves new accounts automatically, so you can log in straight away.
      </p>

      <p class="muted small foot">
        <RouterLink to="/admin">Admin</RouterLink>
      </p>
    </div>
  </div>
</template>

<style scoped>
.wrap { display: flex; justify-content: center; padding-top: 6vh; }
.card { width: 100%; max-width: 420px; }
h1 { margin: 0 0 6px; font-size: 24px; }
.intro { margin: 0 0 18px; }
.tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.tabs button { flex: 1; }
.tabs button.active { border-color: var(--accent-dim); color: var(--accent); }
.full { width: 100%; }
.foot { margin: 14px 0 0; text-align: center; }
</style>
