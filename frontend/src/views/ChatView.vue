<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { api, tokens } from '../api'
import DestinationCard from '../components/DestinationCard.vue'
import MemorySidebar from '../components/MemorySidebar.vue'

const router = useRouter()

const messages = ref([])
const draft = ref('')
const busy = ref(false)
const error = ref('')
const profile = ref(null)
const visited = ref([])
const lastWrites = ref([])
const scroller = ref(null)

const SUGGESTIONS = [
  "I'm in Thailand with 6 weeks left. Laos or Vietnam next?",
  "I'm on a shoestring budget and prefer slow travel.",
  'What do you remember about my trip?'
]

onMounted(loadProfile)

async function loadProfile() {
  try {
    const res = await api.getProfile()
    profile.value = res.profile
    visited.value = res.visited_history
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      tokens.clearUser()
      router.push('/login')
    } else {
      error.value = e.message
    }
  }
}

async function send(text) {
  const message = (text ?? draft.value).trim()
  if (!message || busy.value) return

  error.value = ''
  draft.value = ''
  messages.value.push({ role: 'user', text: message })
  busy.value = true
  await scrollDown()

  try {
    const res = await api.chat(message)
    messages.value.push({
      role: 'assistant',
      text: res.reply,
      comparison: res.comparison || [],
      agents: res.agents_fired || [],
      sources: res.retrieved_sources || [],
      traceId: res.trace_id,
      showDetail: false
    })
    if (res.profile) profile.value = res.profile
    if (res.visited_history) visited.value = res.visited_history
    lastWrites.value = res.memory_writes || []
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      tokens.clearUser()
      router.push('/login')
      return
    }
    error.value = e.message
    messages.value.push({ role: 'error', text: e.message })
  } finally {
    busy.value = false
    await scrollDown()
  }
}

async function scrollDown() {
  await nextTick()
  const el = scroller.value
  if (el) el.scrollTop = el.scrollHeight
}
</script>

<template>
  <div class="layout">
    <section class="chat panel">
      <div ref="scroller" class="stream">
        <div v-if="!messages.length" class="empty">
          <h2>Where next?</h2>
          <p class="muted">
            I already know what is in your profile on the right. Ask me about two or
            three places and I will weigh season, visas, routes and cost against
            what you have told me.
          </p>
          <div class="suggestions">
            <button v-for="s in SUGGESTIONS" :key="s" class="ghost small" @click="send(s)">
              {{ s }}
            </button>
          </div>
        </div>

        <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
          <div v-if="m.role === 'user'" class="bubble user">{{ m.text }}</div>

          <div v-else-if="m.role === 'error'" class="error">{{ m.text }}</div>

          <div v-else class="assistant-block">
            <div class="bubble assistant">{{ m.text }}</div>

            <div v-if="m.comparison.length" class="cards">
              <DestinationCard v-for="c in m.comparison" :key="c.destination" :card="c" />
            </div>

            <button class="ghost small detail-toggle" @click="m.showDetail = !m.showDetail">
              {{ m.showDetail ? 'Hide' : 'Show' }} what ran
              ({{ m.agents.length }} steps, {{ m.sources.length }} passages)
            </button>

            <div v-if="m.showDetail" class="detail">
              <h5>Agents and tools</h5>
              <ul>
                <li v-for="(a, j) in m.agents" :key="j">
                  <span class="mono">{{ a.name }}</span>
                  <span class="tag" :class="a.status === 'ok' ? 'go' : 'avoid'">{{ a.status }}</span>
                  <span v-if="a.duration_ms != null" class="muted small">{{ a.duration_ms }}ms</span>
                  <div v-if="a.summary" class="muted small summary">{{ a.summary }}</div>
                </li>
              </ul>

              <h5>Retrieved passages</h5>
              <ul v-if="m.sources.length">
                <li v-for="(s, j) in m.sources" :key="j">
                  <span class="mono">{{ s.id }}</span>
                  <span class="muted small">{{ s.namespace }} · {{ s.score }}</span>
                </li>
              </ul>
              <p v-else class="muted small">No passages retrieved on this turn.</p>

              <p v-if="m.traceId" class="muted small mono trace">trace {{ m.traceId }}</p>
            </div>
          </div>
        </div>

        <div v-if="busy" class="thinking muted small">
          Running the specialists…
        </div>
      </div>

      <div v-if="error" class="error compose-error">{{ error }}</div>

      <form class="compose" @submit.prevent="send()">
        <input
          v-model="draft"
          :disabled="busy"
          placeholder="Where should I go next?"
          aria-label="Message"
        />
        <button class="primary" :disabled="busy || !draft.trim()" type="submit">Send</button>
      </form>
    </section>

    <MemorySidebar :profile="profile" :visited="visited" :writes="lastWrites" />
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 18px;
  max-width: 1180px;
  margin: 0 auto;
  align-items: start;
}
@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
}

.chat { display: flex; flex-direction: column; height: calc(100vh - 105px); padding: 0; }

.stream { flex: 1; overflow-y: auto; padding: 18px; display: flex; flex-direction: column; gap: 16px; }

.empty { margin: auto 0; text-align: center; padding: 20px; }
.empty h2 { margin: 0 0 8px; font-size: 20px; }
.empty p { max-width: 460px; margin: 0 auto 18px; font-size: 14px; }
.suggestions { display: flex; flex-direction: column; gap: 8px; align-items: center; }
.suggestions button { max-width: 420px; }

.msg.user { display: flex; justify-content: flex-end; }

.bubble { padding: 11px 14px; border-radius: 12px; max-width: 88%; white-space: pre-wrap; }
.bubble.user { background: var(--accent-dim); color: #e9fff4; border-bottom-right-radius: 4px; }
.bubble.assistant { background: var(--panel-2); border: 1px solid var(--line); border-bottom-left-radius: 4px; }

.assistant-block { display: flex; flex-direction: column; gap: 12px; align-items: flex-start; width: 100%; }

.cards { display: flex; flex-direction: column; gap: 10px; width: 100%; }

.detail-toggle { align-self: flex-start; }
.detail {
  width: 100%;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px 14px;
}
.detail h5 { margin: 10px 0 6px; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }
.detail h5:first-child { margin-top: 0; }
.detail ul { margin: 0; padding: 0; list-style: none; }
.detail li { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 5px; font-size: 13px; }
.summary { flex-basis: 100%; }
.trace { margin: 12px 0 0; }

.thinking { padding: 4px 2px; }

.compose { display: flex; gap: 10px; padding: 14px 18px; border-top: 1px solid var(--line); }
.compose-error { margin: 0 18px; }
</style>
