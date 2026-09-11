<script setup>
// Admin panel. Gated by its own token kind, obtained with ADMIN_PASSWORD - a
// regular user's token cannot reach any /admin route.
import { ref, onMounted } from 'vue'
import { api, tokens } from '../api'

const authed = ref(false)
const password = ref('')
const users = ref([])
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
    users.value = await api.adminUsers()
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
}
</script>

<template>
  <div class="wrap">
    <div v-if="!authed" class="panel card">
      <h1>Admin</h1>
      <p class="muted small">Approve or reject new Onward accounts.</p>
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
          <tbody>
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
          </tbody>
        </table>
        <p v-else class="muted small">No accounts registered yet.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wrap { max-width: 900px; margin: 0 auto; }
.card { max-width: 400px; margin: 6vh auto 0; }
h1 { margin: 0 0 4px; font-size: 22px; }
.full { width: 100%; }
.foot { margin: 14px 0 0; text-align: center; }

.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }

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
.actions { display: flex; gap: 6px; justify-content: flex-end; }
</style>
