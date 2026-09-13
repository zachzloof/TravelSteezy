<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { tokens } from './api'
import BugReportButton from './components/BugReportButton.vue'

const route = useRoute()
const router = useRouter()

// route.path is read first so it's always tracked as a reactive dependency -
// otherwise, if tokens.user() started out falsy (the /login screen), `&&`
// short-circuits before ever reading route.path, and this computed would
// never re-run on later navigation. That left the nav bar stuck hidden after
// a client-side login until a full page reload forced a fresh evaluation.
const loggedIn = computed(() => route.path !== '/login' && !!tokens.user())
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
        <span>Travel Steezy</span>
        <span class="tagline hide-narrow">where next?</span>
      </div>

      <nav v-if="loggedIn">
        <RouterLink to="/chat">Chat</RouterLink>
        <RouterLink to="/preferences">My Preferences</RouterLink>
        <RouterLink to="/memory">Memory</RouterLink>
        <span class="who hide-narrow">{{ username }}</span>
        <button class="ghost small" @click="logout">Log out</button>
      </nav>
    </header>

    <main>
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>

    <BugReportButton v-if="loggedIn" />
  </div>
</template>

<style scoped>
.shell { display: flex; flex-direction: column; min-height: 100%; }

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  height: var(--header-h);
  padding: 0 clamp(14px, 3vw, 32px);
  border-bottom: 1px solid var(--line);
  background: var(--panel);
  background: color-mix(in srgb, var(--panel) 88%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  /* Always reachable: a page like Preferences that scrolls its own content
     used to let the only way back to Chat scroll off the top with it. */
  position: sticky;
  top: 0;
  z-index: 20;
}
header::after {
  content: '';
  position: absolute;
  left: 0; right: 0; bottom: -1px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent-dim) 20%, var(--sky-soft) 60%, transparent);
  opacity: .8;
}

.brand { display: flex; align-items: baseline; gap: 9px; font-weight: 700; font-size: 17px; flex: none; }
.mark {
  color: var(--on-accent);
  background: var(--accent-grad);
  display: inline-grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  font-size: 15px;
  box-shadow: var(--glow-accent);
  transition: transform var(--dur) var(--ease-spring), box-shadow var(--dur) ease;
}
.brand:hover .mark {
  transform: rotate(-12deg) scale(1.08);
  box-shadow: 0 0 0 1px var(--accent-bright), 0 10px 24px -6px rgba(226, 129, 47, .6);
}
.brand span:not(.mark) { background: linear-gradient(90deg, var(--text), var(--text) 60%, var(--accent-bright)); -webkit-background-clip: text; background-clip: text; }
.tagline { color: var(--muted); font-weight: 400; font-size: 13px; -webkit-text-fill-color: var(--muted); }

nav { display: flex; align-items: center; gap: 4px; overflow-x: auto; scrollbar-width: none; }
nav::-webkit-scrollbar { display: none; }
nav a {
  position: relative;
  color: var(--muted);
  text-decoration: none;
  font-size: 14px;
  font-weight: 550;
  padding: 7px 12px;
  border-radius: 999px;
  white-space: nowrap;
  transition: background-color var(--dur-fast) ease, color var(--dur-fast) ease, transform var(--dur-fast) ease;
}
nav a:hover { color: var(--text); background: var(--panel-2); transform: translateY(-1px); }
nav a.router-link-active {
  color: var(--on-accent);
  background: var(--accent-grad);
  box-shadow: var(--glow-accent);
}
.who { color: var(--muted); font-size: 13px; margin-left: 6px; white-space: nowrap; }

main { flex: 1; padding: clamp(16px, 3vw, 32px) clamp(14px, 3vw, 32px); }
</style>
