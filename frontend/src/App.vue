<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { tokens } from './api'

const route = useRoute()
const router = useRouter()

const loggedIn = computed(() => !!tokens.user() && route.path !== '/login')
const username = computed(() => tokens.username())

function logout() {
  tokens.clearUser()
  router.push('/login')
}
</script>

<template>
  <div class="shell">
    <header>
      <div class="brand">
        <span class="mark">◈</span>
        <span>Onward</span>
        <span class="tagline hide-narrow">where next?</span>
      </div>

      <nav v-if="loggedIn">
        <RouterLink to="/chat">Chat</RouterLink>
        <RouterLink to="/preferences">My Preferences</RouterLink>
        <span class="who hide-narrow">{{ username }}</span>
        <button class="ghost small" @click="logout">Log out</button>
      </nav>
    </header>

    <main>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.shell { display: flex; flex-direction: column; min-height: 100%; }

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--line);
  background: var(--panel);
}

.brand { display: flex; align-items: baseline; gap: 9px; font-weight: 650; font-size: 17px; }
.mark { color: var(--accent); font-size: 18px; }
.tagline { color: var(--muted); font-weight: 400; font-size: 13px; }

nav { display: flex; align-items: center; gap: 16px; }
nav a { color: var(--muted); text-decoration: none; font-size: 14px; }
nav a:hover { color: var(--text); }
nav a.router-link-active { color: var(--accent); }
.who { color: var(--muted); font-size: 13px; }

main { flex: 1; padding: 20px; }
</style>
