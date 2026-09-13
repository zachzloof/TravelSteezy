<script setup>
// Admin panel. Gated by its own token kind, obtained with ADMIN_PASSWORD - a
// regular user's token cannot reach any /admin route.
import { ref, onMounted } from 'vue'
import { api, tokens } from '../api'

const authed = ref(false)
const password = ref('')
const users = ref([])
const bugs = ref([])
const openBugId = ref(null)
const copiedId = ref(null)
const error = ref('')
const busy = ref(false)

onMounted(() => {
  if (tokens.admin()) refresh()
})

async function login() {
  error.value = ''
  busy.value = true
  try {
    const res = await api.adminLogin(password.value)
    tokens.setAdmin(res.access_token)
    password.value = ''
    await refresh()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function refresh() {
  error.value = ''
  try {
    ;[users.value, bugs.value] = await Promise.all([api.adminUsers(), api.adminBugs()])
    authed.value = true
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      tokens.clearAdmin()
      authed.value = false
    } else {
      error.value = e.message
    }
  }
}

function toggleBug(id) {
  openBugId.value = openBugId.value === id ? null : id
}

async function copyBug(bug) {
  try {
    await navigator.clipboard.writeText(bug.trace_text)
    copiedId.value = bug.id
    setTimeout(() => {
      if (copiedId.value === bug.id) copiedId.value = null
    }, 1500)
  } catch {
    error.value = 'Could not copy to clipboard - select and copy the text manually.'
  }
}

async function toggleResolved(bug) {
  busy.value = true
  error.value = ''
  try {
    const updated = await api.adminResolveBug(bug.id)
    const i = bugs.value.findIndex((b) => b.id === bug.id)
    if (i !== -1) bugs.value[i] = updated
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function act(user, action) {
  busy.value = true
  error.value = ''
  try {
    await (action === 'approve' ? api.adminApprove(user.id) : api.adminReject(user.id))
    await refresh()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

function logout() {
  tokens.clearAdmin()
  authed.value = false
  users.value = []
  bugs.value = []
}
</script>

<template>
  <div class="wrap">
    <div v-if="!authed" class="panel card fade-in-up">
      <h1>Admin</h1>
      <p class="muted small">Approve or reject new Travel Steezy accounts.</p>
      <div v-if="error" class="error">{{ error }}</div>
      <form @submit.prevent="login">
        <div class="field">
          <label for="ap">Admin password</label>
          <input id="ap" v-model="password" type="password" autocomplete="current-password" required />
        </div>
        <button class="primary full" :disabled="busy" type="submit">
          {{ busy ? 'Checking…' : 'Log in as admin' }}
        </button>
      </form>
      <p class="muted small foot"><RouterLink to="/login">Back to the app</RouterLink></p>
    </div>

    <div v-else>
      <div class="head">
        <h1>Accounts</h1>
        <div class="row">
          <button class="ghost small" :disabled="busy" @click="refresh">Refresh</button>
          <button class="ghost small" @click="logout">Log out</button>
        </div>
      </div>

      <div v-if="error" class="error">{{ error }}</div>

      <div class="panel">
        <table v-if="users.length">
          <thead>
            <tr>
              <th>ID</th><th>Username</th><th>Status</th><th>Registered</th><th>Last seen</th><th></th>
            </tr>
          </thead>
          <TransitionGroup tag="tbody" name="fade-slide">
            <tr v-for="u in users" :key="u.id">
              <td class="mono muted">{{ u.id }}</td>
              <td>{{ u.username }}</td>
              <td><span class="tag" :class="{ go: u.status === 'approved', maybe: u.status === 'pending', avoid: u.status === 'rejected' }">{{ u.status }}</span></td>
              <td class="muted small">{{ u.created_at || '—' }}</td>
              <td class="muted small">{{ u.last_seen_at || 'never' }}</td>
              <td class="actions">
                <button v-if="u.status !== 'approved'" class="small" :disabled="busy" @click="act(u, 'approve')">Approve</button>
                <button v-if="u.status !== 'rejected'" class="small danger" :disabled="busy" @click="act(u, 'reject')">Reject</button>
              </td>
            </tr>
          </TransitionGroup>
        </table>
        <p v-else class="muted small">No accounts registered yet.</p>
      </div>

      <div class="head bugs-head">
        <h1>Bug reports</h1>
      </div>

      <div class="panel">
        <div v-if="bugs.length" class="bug-list">
          <div v-for="b in bugs" :key="b.id" class="bug" :class="{ resolved: b.status === 'resolved' }">
            <div class="bug-row" @click="toggleBug(b.id)">
              <span class="tag" :class="{ go: b.status === 'resolved', maybe: b.status === 'open' }">{{ b.status }}</span>
              <span class="bug-desc">{{ b.description }}</span>
              <span class="muted small hide-narrow">{{ b.username }}</span>
              <span class="muted small hide-narrow">{{ b.created_at }}</span>
            </div>
            <div v-if="openBugId === b.id" class="bug-detail">
              <pre class="mono trace-text">{{ b.trace_text }}</pre>
              <div class="actions">
                <a v-if="b.trace_url" :href="b.trace_url" target="_blank" rel="noopener" class="muted small">Open Langfuse trace ↗</a>
                <button class="small" @click="copyBug(b)">{{ copiedId === b.id ? 'Copied!' : 'Copy trace' }}</button>
                <button class="ghost small" :disabled="busy" @click="toggleResolved(b)">
                  {{ b.status === 'resolved' ? 'Reopen' : 'Mark resolved' }}
                </button>
              </div>
            </div>
          </div>
        </div>
        <p v-else class="muted small">No bug reports yet.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wrap { max-width: var(--container); margin: 0 auto; }
.card { max-width: 420px; margin: 6vh auto 0; border-radius: var(--radius-lg); box-shadow: var(--shadow-md); }
h1 { margin: 0 0 4px; font-size: 22px; }
.full { width: 100%; }
.foot { margin: 14px 0 0; text-align: center; }

.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }

.panel { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th {
  text-align: left;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--muted);
  font-weight: 500;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}
td { padding: 10px 8px 10px 0; border-bottom: 1px solid var(--line); }
tbody tr { transition: background-color var(--dur-fast) ease; }
tbody tr:hover { background-color: var(--panel-2); }
.actions { display: flex; gap: 6px; justify-content: flex-end; align-items: center; }

.bugs-head { margin-top: 28px; }

.bug-list { display: flex; flex-direction: column; }
.bug { border-bottom: 1px solid var(--line); }
.bug:last-child { border-bottom: none; }
.bug.resolved { opacity: .6; }

.bug-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 4px;
  cursor: pointer;
}
.bug-row:hover { background-color: var(--panel-2); }
.bug-desc { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.bug-detail { padding: 0 4px 14px; }
.trace-text {
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: 10px;
  font-size: 12.5px;
  max-height: 320px;
  overflow-y: auto;
  margin: 0 0 10px;
}
.bug-detail .actions { justify-content: flex-start; }
</style>
