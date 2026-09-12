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
    <div class="orb orb-a" aria-hidden="true" />
    <div class="orb orb-b" aria-hidden="true" />
    <div class="panel card fade-in-up">
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
.wrap {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - var(--header-h) - 2 * clamp(16px, 3vw, 32px));
  padding: 4vh 0;
  overflow: clip;
}

@keyframes floatOrb {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(3%, -4%) scale(1.06); }
}
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  z-index: 0;
  pointer-events: none;
  animation: floatOrb 14s ease-in-out infinite;
}
.orb-a { width: 360px; height: 360px; left: -80px; top: -60px; background: radial-gradient(circle, var(--accent-soft), transparent 70%); }
.orb-b { width: 320px; height: 320px; right: -70px; bottom: -60px; background: radial-gradient(circle, var(--moss-soft), transparent 70%); animation-delay: -7s; }

.card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 440px;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  border-color: color-mix(in srgb, var(--line) 70%, var(--accent-dim) 30%);
}
h1 {
  margin: 0 0 6px;
  font-size: 26px;
  background: linear-gradient(90deg, var(--text), var(--accent-bright));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.intro { margin: 0 0 20px; }
.tabs { display: flex; gap: 8px; margin-bottom: 18px; background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 4px; }
.tabs button { flex: 1; border-color: transparent; background: transparent; transition: all var(--dur) var(--ease-out); }
.tabs button.active { border-color: var(--accent); background: var(--accent-soft); color: var(--accent-bright); box-shadow: 0 2px 10px -4px rgba(226, 129, 47, .4); }
.full { width: 100%; }
.foot { margin: 14px 0 0; text-align: center; }
</style>
