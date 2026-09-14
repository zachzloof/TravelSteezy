<script setup>
// Admin panel. Gated by its own token kind, obtained with ADMIN_PASSWORD - a
// regular user's token cannot reach any /admin route.
import { computed, ref, onMounted } from 'vue'
import { api, tokens } from '../api'
import SegmentedTabs from '../components/SegmentedTabs.vue'

const authed = ref(false)
const password = ref('')
const users = ref([])
const bugs = ref([])
const openBugId = ref(null)
const copiedId = ref(null)
const error = ref('')
const busy = ref(false)
const tab = ref('accounts')

const openBugs = computed(() => bugs.value.filter((b) => b.status !== 'resolved').length)
const TABS = computed(() => [
  { id: 'accounts', label: 'Accounts', count: users.value.length },
  { id: 'bugs', label: 'Bug reports', count: openBugs.value }
])

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

const STATUS_CLASS = { approved: 'go', pending: 'maybe', rejected: 'avoid' }
</script>

<template>
  <div class="page">
    <!-- ------------------------------------------------------------ login -->
    <div v-if="!authed" class="login">
      <div class="panel card fade-in-up">
        <h1>Admin</h1>
        <p class="muted small intro">Approve accounts and triage bug reports.</p>
        <div v-if="error" class="error msg">{{ error }}</div>
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
    </div>

    <!-- ------------------------------------------------------------ panel -->
    <template v-else>
      <header class="page-head">
        <div>
          <h1 class="grad-text">Admin</h1>
          <p class="muted small">Accounts and bug reports for this deployment.</p>
        </div>
        <div class="cluster">
          <button class="small" :disabled="busy" @click="refresh">Refresh</button>
          <button class="ghost small" @click="logout">Log out</button>
        </div>
      </header>

      <SegmentedTabs v-model="tab" :tabs="TABS" label="Admin sections" />

      <div v-if="error" class="error">{{ error }}</div>

      <!-- --------------------------------------------------- accounts -->
      <section v-if="tab === 'accounts'" class="panel">
        <table v-if="users.length" class="users">
          <thead>
            <tr>
              <th>ID</th><th>Username</th><th>Status</th><th>Registered</th><th>Last seen</th><th></th>
            </tr>
          </thead>
          <TransitionGroup tag="tbody" name="fade-slide">
            <tr v-for="u in users" :key="u.id">
              <td data-label="ID" class="mono muted">{{ u.id }}</td>
              <td data-label="Username" class="who">{{ u.username }}</td>
              <td data-label="Status"><span class="tag" :class="STATUS_CLASS[u.status]">{{ u.status }}</span></td>
              <td data-label="Registered" class="muted small">{{ u.created_at || '—' }}</td>
              <td data-label="Last seen" class="muted small">{{ u.last_seen_at || 'never' }}</td>
              <td class="ops">
                <button v-if="u.status !== 'approved'" class="small" :disabled="busy" @click="act(u, 'approve')">Approve</button>
                <button v-if="u.status !== 'rejected'" class="small danger" :disabled="busy" @click="act(u, 'reject')">Reject</button>
              </td>
            </tr>
          </TransitionGroup>
        </table>
        <div v-else class="empty-state">
          <span class="glyph" aria-hidden="true">👤</span>
          <p>No accounts registered yet.</p>
        </div>
      </section>

      <!-- ------------------------------------------------------- bugs -->
      <section v-else class="panel">
        <div v-if="bugs.length" class="bug-list">
          <div v-for="b in bugs" :key="b.id" class="bug" :class="{ resolved: b.status === 'resolved' }">
            <button class="bug-row" :aria-expanded="openBugId === b.id" @click="toggleBug(b.id)">
              <span class="tag" :class="{ go: b.status === 'resolved', maybe: b.status === 'open' }">{{ b.status }}</span>
              <span class="bug-desc">{{ b.description }}</span>
              <span class="bug-meta muted small">{{ b.username }} · {{ b.created_at }}</span>
            </button>
            <div v-if="openBugId === b.id" class="bug-detail">
              <pre class="mono trace-text">{{ b.trace_text }}</pre>
              <div class="cluster">
                <button class="small" @click="copyBug(b)">{{ copiedId === b.id ? 'Copied!' : 'Copy trace' }}</button>
                <button class="ghost small" :disabled="busy" @click="toggleResolved(b)">
                  {{ b.status === 'resolved' ? 'Reopen' : 'Mark resolved' }}
                </button>
                <a v-if="b.trace_url" :href="b.trace_url" target="_blank" rel="noopener" class="small">Open Langfuse trace ↗</a>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <span class="glyph" aria-hidden="true">🐞</span>
          <p>No bug reports yet.</p>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
/* ------------------------------------------------------------------ login */
.login { display: flex; justify-content: center; align-items: center; min-height: calc(var(--view-h) - 2 * var(--gutter)); }
.card { width: 100%; max-width: 420px; padding: var(--sp-6); border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); }
.card h1 { margin: 0 0 var(--sp-1); font-size: 24px; }
.intro { margin: 0 0 var(--sp-5); }
.msg { margin-bottom: var(--sp-4); }
.foot { margin: var(--sp-4) 0 0; text-align: center; }

/* --------------------------------------------------------------- accounts */
table.users { width: 100%; border-collapse: collapse; font-size: 14px; }
th {
  text-align: left;
  font-size: var(--fs-xs);
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--muted);
  font-weight: 600;
  padding: 0 8px 9px 0;
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}
td { padding: 11px 8px 11px 0; border-bottom: 1px solid var(--line); vertical-align: middle; }
tbody tr:last-child td { border-bottom: none; }
@media (hover: hover) { tbody tr:hover { background-color: var(--panel-2); } }
.who { font-weight: 550; overflow-wrap: anywhere; }
.ops { display: flex; gap: 6px; justify-content: flex-end; align-items: center; flex-wrap: wrap; }

/* Six columns do not fit a phone. Each account becomes its own labelled card,
   with the approve/reject buttons on a full-width row of their own. */
@media (max-width: 760px) {
  table.users thead { display: none; }
  table.users, table.users tbody, table.users tr, table.users td { display: block; width: 100%; }
  table.users tr {
    border: 1px solid var(--line);
    border-radius: var(--radius-sm);
    background: var(--bg);
    padding: var(--sp-3);
    margin-bottom: var(--sp-2);
  }
  table.users td { border: none; padding: 3px 0; display: flex; gap: var(--sp-3); align-items: baseline; }
  table.users td::before {
    content: attr(data-label);
    flex: none;
    width: 82px;
    color: var(--muted);
    font-size: var(--fs-xs);
    text-transform: uppercase;
    letter-spacing: .04em;
  }
  table.users td.ops { justify-content: flex-start; padding-top: var(--sp-3); }
  table.users td.ops button { flex: 1 1 auto; }
}

/* ------------------------------------------------------------------- bugs */
.bug-list { display: flex; flex-direction: column; }
.bug { border-bottom: 1px solid var(--line); }
.bug:last-child { border-bottom: none; }
.bug.resolved { opacity: .6; }

.bug-row {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px var(--sp-3);
  align-items: center;
  width: 100%;
  text-align: left;
  padding: var(--sp-3) var(--sp-1);
  background: none;
  border: none;
  border-radius: var(--radius-sm);
}
.bug-row:hover:not(:disabled) { background-color: var(--panel-2); transform: none; }
.bug-desc { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
/* The reporter and timestamp drop onto their own line under the description
   rather than being hidden entirely on a phone - on a triage screen, who
   reported it and when is half the information. */
.bug-meta { grid-column: 2; }

.bug-detail { padding: 0 var(--sp-1) var(--sp-4); }
.trace-text {
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: var(--sp-3);
  font-size: 12.5px;
  max-height: 320px;
  overflow-y: auto;
  margin: 0 0 var(--sp-3);
}
</style>
