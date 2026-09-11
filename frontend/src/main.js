import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

import LoginView from './views/LoginView.vue'
import ChatView from './views/ChatView.vue'
import PreferencesView from './views/PreferencesView.vue'
import AdminView from './views/AdminView.vue'
import { tokens } from './api'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/login', component: LoginView, meta: { public: true } },
  { path: '/chat', component: ChatView },
  { path: '/preferences', component: PreferencesView },
  // Admin is its own route with its own token; a regular user's token cannot
  // satisfy the backend's admin dependency, so this is invisible to them.
  { path: '/admin', component: AdminView, meta: { public: true, admin: true } }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  if (!to.meta.public && !tokens.user()) {
    return { path: '/login', query: { next: to.path } }
  }
  return true
})

createApp(App).use(router).mount('#app')
