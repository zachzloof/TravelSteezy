import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

import LoginView from './views/LoginView.vue'
import WelcomeView from './views/WelcomeView.vue'
import ChatView from './views/ChatView.vue'
import PreferencesView from './views/PreferencesView.vue'
import MemoryView from './views/MemoryView.vue'
import AdminView from './views/AdminView.vue'
import { api, session, tokens } from './api'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/login', component: LoginView, meta: { public: true } },
  // Onboarding is a page of its own rather than the first few turns of the chat.
  // `skipGate` marks it as the one authenticated route the onboarding redirect
  // below must never bounce, which would otherwise be an infinite loop.
  { path: '/welcome', component: WelcomeView, meta: { skipGate: true } },
  { path: '/chat', component: ChatView },
  { path: '/preferences', component: PreferencesView },
  // A debug tool, so it stays reachable even mid-onboarding - the whole point
  // of it is to inspect memory when something (possibly onboarding itself) is
  // not behaving as expected.
  { path: '/memory', component: MemoryView, meta: { skipGate: true } },
  // Admin is its own route with its own token; a regular user's token cannot
  // satisfy the backend's admin dependency, so this is invisible to them.
  { path: '/admin', component: AdminView, meta: { public: true, admin: true } }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  if (!to.meta.public && !tokens.user()) {
    return { path: '/login', query: { next: to.path } }
  }
  // session.onboarded caches the positive answer for the rest of the
  // session, so the gate costs one request rather than one per navigation.
  // It is cleared on login and logout, so it can never outlive its account.
  if (to.meta.public || to.meta.skipGate || session.onboarded) return true

  try {
    const travel = await api.getTravel()
    const status = travel?.onboarding?.status
    if (status === 'complete' || status === 'skipped') {
      session.onboarded = true
      return true
    }
    // A brand-new account gets the welcome page, not a chat window asking it
    // questions. `next` is carried so finishing lands them where they meant to go.
    return { path: '/welcome', query: to.path === '/chat' ? {} : { next: to.path } }
  } catch {
    // Never let a failed gate check lock someone out of their own app. If we
    // cannot tell, let them through - the worst case is a returning user seeing
    // the chat when they might have seen onboarding.
    return true
  }
})

createApp(App).use(router).mount('#app')
