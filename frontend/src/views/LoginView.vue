<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, tokens } from '../api'

const route = useRoute()
const router = useRouter()

const mode = ref('login')
const username = ref('')
const password = ref('')
const accessCode = ref('')
const error = ref('')
const notice = ref('')
const busy = ref(false)
const autoApprove = ref(false)
const accessCodeConfigured = ref(false)

onMounted(async () => {
  try {
    const health = await api.health()
    autoApprove.value = !!health?.auth?.auto_approve
    accessCodeConfigured.value = !!health?.auth?.access_code_configured
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
      const res = await api.register(username.value.trim(), password.value, accessCode.value.trim())
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

function setMode(next) {
  mode.value = next
  error.value = ''
}
</script>

<template>
  <div class="wrap">
    <div class="orb orb-a" aria-hidden="true" />
    <div class="orb orb-b" aria-hidden="true" />

    <div class="panel card fade-in-up">
      <h1 class="grad-text">Travel Steezy</h1>
      <p class="muted small intro">
        A travel assistant for long-term backpackers. Tell it where you are, what
        your budget is and how long you have, and it will weigh up where to go next
        on weather, visas, routes and cost.
      </p>

      <div class="tabs" role="tablist" aria-label="Log in or register">
        <button
          role="tab"
          :aria-selected="mode === 'login'"
          :class="{ active: mode === 'login' }"
          @click="setMode('login')"
        >Log in</button>
        <button
          role="tab"
          :aria-selected="mode === 'register'"
          :class="{ active: mode === 'register' }"
          @click="setMode('register')"
        >Register</button>
      </div>

      <div v-if="error" class="error msg">{{ error }}</div>
      <div v-if="notice" class="notice msg">{{ notice }}</div>

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
        <div v-if="mode === 'register'" class="field">
          <label for="ac">Access code <span class="muted small">(optional)</span></label>
          <input id="ac" v-model="accessCode" autocomplete="off" />
        </div>
        <button class="primary full" :disabled="busy" type="submit">
          {{ busy ? 'Working…' : mode === 'login' ? 'Log in' : 'Create account' }}
        </button>
      </form>

      <p v-if="mode === 'register'" class="muted small foot">
        <template v-if="autoApprove">
          This deployment approves new accounts automatically, so you can log in straight away.
        </template>
        <template v-else-if="accessCodeConfigured">
          New accounts need admin approval unless you enter a valid access code, which
          approves you instantly.
        </template>
        <template v-else>
          New accounts need admin approval before you can log in.
        </template>
      </p>

      <p class="muted small foot admin-link">
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
  min-height: calc(var(--view-h) - 2 * var(--gutter));
  padding: var(--sp-5) 0;
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
@media (max-width: 560px) { .orb { display: none; } }

.card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 430px;
  padding: var(--sp-6);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  border-color: color-mix(in srgb, var(--line) 70%, var(--accent-dim) 30%);
}
@media (max-width: 560px) { .card { padding: var(--sp-5); } }

h1 { margin: 0 0 var(--sp-2); font-size: clamp(24px, 6vw, 28px); }
.intro { margin: 0 0 var(--sp-5); }

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: var(--sp-5);
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-pill);
  padding: 4px;
}
.tabs button {
  flex: 1;
  border-color: transparent;
  background: transparent;
  border-radius: var(--radius-pill);
  font-weight: 600;
  font-size: 14px;
  color: var(--muted);
}
.tabs button:hover:not(.active) { color: var(--text); background: var(--panel-2); transform: none; }
.tabs button.active {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent-bright);
}

.msg { margin-bottom: var(--sp-4); }
.foot { margin: var(--sp-4) 0 0; text-align: center; }
.admin-link { opacity: .7; }
.admin-link a { display: inline-block; padding: 8px 14px; text-decoration: none; }
</style>
