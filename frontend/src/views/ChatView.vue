<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { api, tokens } from '../api'
import DestinationCard from '../components/DestinationCard.vue'
import MemorySidebar from '../components/MemorySidebar.vue'
import TripPanel from '../components/TripPanel.vue'
import ReviewCard from '../components/ReviewCard.vue'
import CatchUpCard from '../components/CatchUpCard.vue'
import Markdown from '../components/Markdown.vue'

const router = useRouter()

const messages = ref([])
const draft = ref('')
const busy = ref(false)
const error = ref('')
const profile = ref(null)
const visited = ref([])
const lastWrites = ref([])
const scroller = ref(null)

const travelHistory = ref([])
const wishlist = ref([])
const interests = ref([])
const reviewPrompt = ref(null)
const reviewBusy = ref(false)

const catchup = ref(null)
const catchupBusy = ref(false)

// Onboarding is no longer part of this screen. A brand-new account is routed to
// /welcome before it ever gets here, so the chat is only ever a chat.
const SUGGESTIONS = [
  "I'm in Thailand with 6 weeks left. Laos or Vietnam next?",
  'Where should I go next from here?',
  'Any good hostels here, and which area should I stay in?',
  'What do you remember about my trip?'
]

onMounted(async () => {
  await Promise.all([loadProfile(), loadTravel(), loadCatchup()])
})

async function loadCatchup() {
  try {
    const res = await api.getCatchup()
    if (res.due) catchup.value = res
  } catch {
    // A failed check must never block the chat itself from loading.
  }
}

async function dismissCatchup() {
  catchupBusy.value = true
  try {
    await api.dismissCatchup()
    catchup.value = null
  } catch (e) {
    error.value = e.message
  } finally {
    catchupBusy.value = false
  }
}

async function updateCatchup(message) {
  // This is a genuine chat turn (it runs through the same /chat pipeline via
  // POST /travel/me/catchup/update), so it is shown in the transcript exactly
  // like any other exchange rather than disappearing silently.
  catchupBusy.value = true
  error.value = ''
  messages.value.push({ role: 'user', text: message })
  await scrollDown()
  try {
    const res = await api.updateCatchup(message)
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
    applyTravel(res)
    if (res.review_prompt) reviewPrompt.value = res.review_prompt
    catchup.value = null
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      tokens.clearUser()
      router.push('/login')
      return
    }
    error.value = e.message
    messages.value.push({ role: 'error', text: e.message })
  } finally {
    catchupBusy.value = false
    await scrollDown()
  }
}

async function loadTravel() {
  try {
    const res = await api.getTravel()
    applyTravel(res)
    if (res.pending_reviews?.length && !reviewPrompt.value) {
      reviewPrompt.value = { location: res.pending_reviews[0] }
    }
  } catch (e) {
    if (e.status !== 401 && e.status !== 403) error.value = e.message
  }
}

function applyTravel(res) {
  if (res.travel_history) travelHistory.value = res.travel_history
  if (res.wishlist) wishlist.value = res.wishlist
  if (res.interests) interests.value = res.interests
}

async function submitReview(payload) {
  reviewBusy.value = true
  try {
    applyTravel(await api.saveReview(payload))
    reviewPrompt.value = null
    messages.value.push({
      role: 'assistant',
      text: `Noted - ${payload.location} saved to your trip history.`,
      comparison: [], agents: [], sources: [], showDetail: false
    })
    await scrollDown()
  } catch (e) {
    error.value = e.message
  } finally {
    reviewBusy.value = false
  }
}

async function dropWishlistItem(location) {
  try {
    applyTravel(await api.dropWishlist(location))
  } catch (e) {
    error.value = e.message
  }
}

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
    applyTravel(res)
    if (res.review_prompt) reviewPrompt.value = res.review_prompt
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
            I already know what is in your profile on the right — where you have been,
            what you rated it, and how you travel. Ask me about two or three places and
            I will weigh season, visas, routes and cost against all of it.
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
            <div class="bubble assistant"><Markdown :text="m.text" /></div>

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

      <CatchUpCard
        v-if="catchup"
        class="review-slot"
        :summary="catchup.summary"
        :days-since="catchup.days_since"
        :busy="catchupBusy"
        @update="updateCatchup"
        @dismiss="dismissCatchup"
      />

      <ReviewCard
        v-if="reviewPrompt"
        class="review-slot"
        :location="reviewPrompt.location"
        :busy="reviewBusy"
        @submit="submitReview"
        @dismiss="reviewPrompt = null"
      />

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

    <div class="sidebar">
      <MemorySidebar :profile="profile" :visited="visited" :writes="lastWrites">
        <TripPanel
          :history="travelHistory"
          :wishlist="wishlist"
          :interests="interests"
          @drop-wishlist="dropWishlistItem"
        />
      </MemorySidebar>
    </div>
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

.bubble { padding: 11px 14px; border-radius: 12px; max-width: 88%; }
/* The user's own typed message stays literal plain text - pre-wrap so their own
   line breaks survive, and no markdown rendering (it is not the LLM's output). */
.bubble.user { background: var(--accent-dim); color: #e9fff4; border-bottom-right-radius: 4px; white-space: pre-wrap; }
/* The assistant bubble renders real markdown (see components/Markdown.vue), so
   spacing comes from its own paragraph/list styles rather than pre-wrap. */
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

.review-slot { margin: 0 18px 14px; }
.sidebar { min-width: 0; }

.compose { display: flex; gap: 10px; padding: 14px 18px; border-top: 1px solid var(--line); }
.compose-error { margin: 0 18px; }
</style>
