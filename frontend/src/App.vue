<script setup>
// The app shell.
//
// It renders two different navigations from one set of destinations:
//
//   Desktop  — brand on the left, pill nav in the middle, account on the right.
//   Mobile   — a slim top bar that only carries identity and the account menu,
//              and a fixed bottom tab bar for the actual destinations.
//
// The bottom bar is the change that matters on a phone. Nav links in the top
// bar had to share one row with the brand and the username, which meant they
// were either cramped or in a horizontally scrolling strip that hid whichever
// destination you were not currently on. A tab bar puts all three within thumb
// reach, always visible, and frees the top of the screen for content.
//
// Its height is published as --tabbar-h in style.css rather than hard-coded
// here, because every full-height view and every fixed element in the app has
// to stay clear of it.
import { computed, provide, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { tokens } from './api'
import BugReportDialog from './components/BugReportDialog.vue'

const route = useRoute()
const router = useRouter()

// route.path is read first so it's always tracked as a reactive dependency -
// otherwise, if tokens.user() started out falsy (the /login screen), `&&`
// short-circuits before ever reading route.path, and this computed would
// never re-run on later navigation. That left the nav bar stuck hidden after
// a client-side login until a full page reload forced a fresh evaluation.
const loggedIn = computed(() => route.path !== '/login' && !!tokens.user())
const username = computed(() => tokens.username())

// Admin is deliberately absent: it is a separate token and not a destination
// a signed-in traveller has any use for.
const DESTINATIONS = [
  { to: '/chat', label: 'Chat', hint: 'Ask where to go next' },
  { to: '/preferences', label: 'Trip', hint: 'Your profile, route and wishlist' },
  { to: '/memory', label: 'Memory', hint: 'What the assistant remembers' }
]

const menuOpen = ref(false)
watch(() => route.fullPath, () => { menuOpen.value = false })

// Bug reporting is no longer a floating button - on a phone a bottom-right FAB
// landed on top of the chat composer's send button. The dialog is owned here,
// once, and opened from two places: the account menu (reachable on every page)
// and a button inside the chat composer, which is where people actually are
// when something goes wrong and so is the one that gets used.
//
// Provided rather than imported by ChatView so there is a single dialog
// instance in the app instead of one per view that wants to open it.
const bugDialog = ref(null)
function reportBug() {
  menuOpen.value = false
  bugDialog.value?.show()
}
provide('reportBug', reportBug)

function logout() {
  menuOpen.value = false
  tokens.clearUser()
  router.push('/login')
}

const initial = computed(() => (username.value || '?').charAt(0).toUpperCase())
</script>

<template>
  <div class="shell" :class="{ 'has-tabbar': loggedIn }">
    <header>
      <RouterLink :to="loggedIn ? '/chat' : '/login'" class="brand">
        <span class="mark" aria-hidden="true">◈</span>
        <span class="name">Travel Steezy</span>
        <span class="tagline hide-narrow">where next?</span>
      </RouterLink>

      <!-- Desktop destinations. On mobile these live in the bottom tab bar. -->
      <nav v-if="loggedIn" class="top-nav hide-narrow" aria-label="Main">
        <RouterLink v-for="d in DESTINATIONS" :key="d.to" :to="d.to" :title="d.hint">
          {{ d.label }}
        </RouterLink>
      </nav>

      <div v-if="loggedIn" class="account">
        <button
          class="avatar"
          :aria-expanded="menuOpen"
          aria-haspopup="menu"
          :aria-label="`Account: ${username}`"
          @click="menuOpen = !menuOpen"
        >{{ initial }}</button>

        <Transition name="pop">
          <div v-if="menuOpen" class="menu" role="menu">
            <div class="menu-who">
              <span class="menu-name">{{ username }}</span>
              <span class="muted small">Signed in</span>
            </div>
            <button class="menu-item" role="menuitem" @click="reportBug">Report a bug</button>
            <button class="menu-item" role="menuitem" @click="logout">Log out</button>
          </div>
        </Transition>
      </div>
    </header>

    <!-- Closes the account menu on any outside tap without swallowing the tap
         that opened it. Transparent, so it is invisible but still hit-testable. -->
    <div v-if="menuOpen" class="scrim" @click="menuOpen = false" />

    <main>
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>

    <nav v-if="loggedIn" class="tabbar only-narrow" aria-label="Main">
      <RouterLink v-for="d in DESTINATIONS" :key="d.to" :to="d.to" class="tab">
        <span class="tab-icon" aria-hidden="true">
          <svg v-if="d.to === '/chat'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20.5 11.6a7.9 7.9 0 0 1-8.5 7.9 9 9 0 0 1-2.6-.4L4.5 21l1.2-3.6a7.6 7.6 0 0 1-2.2-5.3 7.9 7.9 0 0 1 8.5-7.6 8 8 0 0 1 8.5 7.1z" />
          </svg>
          <svg v-else-if="d.to === '/preferences'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 20c0-2.5 2-3.5 4.5-3.5S14 15 14 12.5 12 9 9.5 9" />
            <circle cx="18.5" cy="17.5" r="2.2" />
            <path d="M6.5 3.5a3 3 0 0 1 3 3c0 2-3 5-3 5s-3-3-3-5a3 3 0 0 1 3-3z" />
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <ellipse cx="12" cy="6" rx="7.5" ry="3" />
            <path d="M4.5 6v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V6" />
            <path d="M4.5 12v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-6" />
          </svg>
        </span>
        <span class="tab-label">{{ d.label }}</span>
      </RouterLink>
    </nav>

    <BugReportDialog v-if="loggedIn" ref="bugDialog" />
  </div>
</template>

<style scoped>
.shell { display: flex; flex-direction: column; min-height: 100%; }

/* The login and admin screens have no tab bar, so nothing should be reserving
   space for one. --tabbar-h is set globally per breakpoint; this switches it
   off for the signed-out shell rather than every consumer special-casing it. */
.shell:not(.has-tabbar) { --tabbar-h: 0px; }

/* ------------------------------------------------------------------ header */
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sp-4);
  height: var(--header-h);
  padding: 0 max(var(--gutter), var(--safe-l)) 0 max(var(--gutter), var(--safe-r));
  padding-top: var(--safe-t);
  border-bottom: 1px solid var(--line);
  background: color-mix(in srgb, var(--panel) 82%, transparent);
  backdrop-filter: blur(14px) saturate(140%);
  -webkit-backdrop-filter: blur(14px) saturate(140%);
  /* Always reachable: a page like Preferences that scrolls its own content
     used to let the only way back to Chat scroll off the top with it. */
  position: sticky;
  top: 0;
  z-index: 20;
  box-sizing: content-box;
}
header::after {
  content: '';
  position: absolute;
  left: 0; right: 0; bottom: -1px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent-dim) 20%, var(--sky-soft) 60%, transparent);
  opacity: .8;
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-weight: 700;
  font-size: 16px;
  flex: none;
  text-decoration: none;
  color: var(--text);
  min-width: 0;
}
.mark {
  color: var(--on-accent);
  background: var(--accent-grad);
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  flex: none;
  border-radius: var(--radius-sm);
  font-size: 15px;
  box-shadow: var(--glow-accent);
  transition: transform var(--dur) var(--ease-spring), box-shadow var(--dur) ease;
}
.name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@media (hover: hover) {
  .brand:hover .mark {
    transform: rotate(-12deg) scale(1.08);
    box-shadow: 0 0 0 1px var(--accent-bright), 0 10px 24px -6px rgba(226, 129, 47, .6);
  }
}
.tagline { color: var(--muted); font-weight: 400; font-size: var(--fs-sm); align-self: baseline; }

/* Under 420px the wordmark alone can crowd out the account button. */
@media (max-width: 420px) {
  .name { font-size: 15px; }
}

/* -------------------------------------------------------------- desktop nav */
.top-nav { display: flex; align-items: center; gap: var(--sp-1); }
.top-nav a {
  position: relative;
  color: var(--muted);
  text-decoration: none;
  font-size: 14px;
  font-weight: 550;
  padding: 8px 14px;
  border-radius: var(--radius-pill);
  white-space: nowrap;
  transition: background-color var(--dur-fast) ease, color var(--dur-fast) ease;
}
.top-nav a:hover { color: var(--text); background: var(--panel-2); }
.top-nav a.router-link-active {
  color: var(--on-accent);
  background: var(--accent-grad);
  box-shadow: var(--glow-accent);
}

/* ----------------------------------------------------------------- account */
.account { position: relative; flex: none; }
.avatar {
  width: 34px;
  height: 34px;
  padding: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
  background: var(--panel-2);
  border: 1px solid var(--line);
}
.avatar:hover:not(:disabled) { border-color: var(--accent-dim); color: var(--accent-bright); }
@media (pointer: coarse) { .avatar { width: 38px; height: 38px; } }

.menu {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  z-index: 30;
  min-width: 190px;
  padding: var(--sp-2);
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
  transform-origin: top right;
}
.menu-who {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: var(--sp-2) var(--sp-3) var(--sp-3);
  border-bottom: 1px solid var(--line);
  margin-bottom: var(--sp-2);
}
.menu-name { font-weight: 600; overflow: hidden; text-overflow: ellipsis; }
.menu-item {
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  padding: 10px var(--sp-3);
  border-radius: var(--radius-sm);
  font-size: 14px;
}
.menu-item:hover:not(:disabled) { background: var(--panel-2); transform: none; }

.scrim { position: fixed; inset: 0; z-index: 19; }

/* -------------------------------------------------------------------- main */
main {
  flex: 1;
  width: 100%;
  padding: var(--gutter) max(var(--gutter), var(--safe-r)) var(--gutter) max(var(--gutter), var(--safe-l));
  /* Clears the fixed tab bar and the iOS home indicator. On desktop
     --tabbar-h is 0, so this collapses back to a plain gutter. */
  padding-bottom: calc(var(--gutter) + var(--tabbar-h) + var(--safe-b));
}

/* ------------------------------------------------------------- mobile tabs */
.tabbar {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  z-index: 25;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  align-items: stretch;
  height: calc(var(--tabbar-h) + var(--safe-b));
  padding-bottom: var(--safe-b);
  background: color-mix(in srgb, var(--panel) 92%, transparent);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  border-top: 1px solid var(--line);
}
.tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  text-decoration: none;
  color: var(--muted);
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: .01em;
  -webkit-tap-highlight-color: transparent;
  transition: color var(--dur-fast) ease;
}
.tab-icon {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  transition: transform var(--dur) var(--ease-spring);
}
.tab-icon svg { width: 22px; height: 22px; }
.tab.router-link-active { color: var(--accent-bright); }
.tab.router-link-active .tab-icon { transform: translateY(-1px) scale(1.06); }
/* The active pill sits behind the icon rather than around the whole tab, so
   the bar keeps its height and the labels stay on one line. */
.tab.router-link-active .tab-icon::before {
  content: '';
  position: absolute;
  width: 40px;
  height: 26px;
  border-radius: var(--radius-pill);
  background: var(--accent-soft);
  z-index: -1;
}
.tab-icon { position: relative; isolation: isolate; }
.tab:active { color: var(--accent); }
</style>
