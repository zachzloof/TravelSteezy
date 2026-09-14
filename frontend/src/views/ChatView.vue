<script setup>
import { computed, inject, ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { api, tokens, lastTrace } from '../api'
import DestinationCard from '../components/DestinationCard.vue'
import MemorySidebar from '../components/MemorySidebar.vue'
import TripPanel from '../components/TripPanel.vue'
import ReviewCard from '../components/ReviewCard.vue'
import CatchUpCard from '../components/CatchUpCard.vue'
import Markdown from '../components/Markdown.vue'
import BottomSheet from '../components/BottomSheet.vue'

const router = useRouter()

const messages = ref([])
const draft = ref('')
const busy = ref(false)
const error = ref('')
const profile = ref(null)
const scroller = ref(null)
const composer = ref(null)

const travelHistory = ref([])
const wishlist = ref([])
const interests = ref([])
const keyInterests = ref([])
const reviewPrompt = ref(null)
const reviewBusy = ref(false)

const catchup = ref(null)
const catchupBusy = ref(false)

// On a phone the trip context is a sheet rather than a column, so it needs
// somewhere to be opened from.
const sheetOpen = ref(false)

// Desktop only: the rail can be collapsed to give the chat column the width
// back. Mobile never renders this — it uses the sheet above instead.
const railOpen = ref(true)

// Opening the bug dialog the app shell owns. Sitting in the composer next to
// Send is the point: reporting a bad answer is worth doing the moment you get
// one, and anything buried in a menu does not get used.
const reportBug = inject('reportBug', null)

// Onboarding is no longer part of this screen. A brand-new account is routed to
// /welcome before it ever gets here, so the chat is only ever a chat.

// A one-line version of the sidebar for the mobile trigger: enough to show the
// assistant is holding real context, and to make it obvious there is more
// behind the tap.
const contextSummary = computed(() => {
  const parts = []
  if (profile.value?.current_location) parts.push(`In ${profile.value.current_location}`)
  if (travelHistory.value.length) {
    parts.push(`${travelHistory.value.length} stop${travelHistory.value.length === 1 ? '' : 's'}`)
  }
  if (wishlist.value.length) parts.push(`${wishlist.value.length} on the list`)
  return parts.join(' · ') || 'Nothing saved yet'
})

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
    pushReply(res)
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

/** Everything that happens to the screen when a /chat response comes back. */
function pushReply(res) {
  messages.value.push({
    role: 'assistant',
    text: res.reply,
    comparison: res.comparison || [],
    agents: res.agents_fired || [],
    sources: res.retrieved_sources || [],
    traceId: res.trace_id,
    showDetail: false
  })
  lastTrace.id = res.trace_id || lastTrace.id
  if (res.profile) profile.value = res.profile
  applyTravel(res)
  if (res.review_prompt) reviewPrompt.value = res.review_prompt
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
  keyInterests.value = res.key_interests || []
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
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      tokens.clearUser()
      router.push('/login')
    } else {
      error.value = e.message
    }
  }
}

async function send() {
  const message = draft.value.trim()
  if (!message || busy.value) return

  error.value = ''
  draft.value = ''
  resizeComposer()
  messages.value.push({ role: 'user', text: message })
  busy.value = true
  await scrollDown()

  try {
    pushReply(await api.chat(message))
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

// The composer grows with the message instead of scrolling a one-line box.
// Capped, so a long paste cannot eat the conversation above it.
function resizeComposer() {
  const el = composer.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 132)}px`
}

function onComposerKey(event) {
  // Enter sends; Shift+Enter is a newline. On a touch keyboard the return key
  // inserts a newline as usual, because there is no Enter to intercept.
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    send()
  }
}

async function scrollDown() {
  await nextTick()
  const el = scroller.value
  if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
}
</script>

<template>
  <div class="layout">
    <section class="chat">
      <!-- Mobile only: the sidebar's headline, and the way into the rest of it. -->
      <button class="context-bar only-narrow" @click="sheetOpen = true">
        <span class="ctx-label">Your trip</span>
        <span class="ctx-summary">{{ contextSummary }}</span>
        <span class="ctx-chev" aria-hidden="true">›</span>
      </button>

      <div ref="scroller" class="stream">
        <div v-if="!messages.length" class="intro fade-in-up">
          <span class="intro-mark" aria-hidden="true">◈</span>
          <h2 class="grad-text">Where next?</h2>
          <p>
            I already know your trip — where you have been, what you rated it, your
            passport, budget and pace. Name a couple of places, or just ask, and I
            will weigh season, visas, routes and cost against all of it.
          </p>
        </div>

        <TransitionGroup name="fade-slide" tag="div" class="stream-inner">
          <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
            <div v-if="m.role === 'user'" class="bubble user">{{ m.text }}</div>

            <div v-else-if="m.role === 'error'" class="error">{{ m.text }}</div>

            <div v-else class="assistant-block">
              <div class="bubble assistant"><Markdown :text="m.text" /></div>

              <div v-if="m.comparison.length" class="cards auto-grid">
                <DestinationCard
                  v-for="(c, ci) in m.comparison"
                  :key="c.destination"
                  :card="c"
                  :style="{ animationDelay: `${ci * 80}ms` }"
                  class="pop-in"
                />
              </div>

              <button class="ghost small detail-toggle" @click="m.showDetail = !m.showDetail">
                <span class="chev" :class="{ open: m.showDetail }" aria-hidden="true">›</span>
                {{ m.agents.length }} steps · {{ m.sources.length }} passages
              </button>

              <Transition name="fade-slide">
                <div v-if="m.showDetail" class="detail">
                  <p class="eyebrow">Agents and tools</p>
                  <ul>
                    <li v-for="(a, j) in m.agents" :key="j">
                      <span class="mono">{{ a.name }}</span>
                      <span class="tag" :class="a.status === 'ok' ? 'go' : 'avoid'">{{ a.status }}</span>
                      <span v-if="a.duration_ms != null" class="muted small">{{ a.duration_ms }}ms</span>
                      <div v-if="a.summary" class="muted small summary">{{ a.summary }}</div>
                    </li>
                  </ul>

                  <p class="eyebrow">Retrieved passages</p>
                  <ul v-if="m.sources.length">
                    <li v-for="(s, j) in m.sources" :key="j">
                      <span class="mono">{{ s.id }}</span>
                      <span class="muted small">{{ s.namespace }} · {{ s.score }}</span>
                    </li>
                  </ul>
                  <p v-else class="muted small">No passages retrieved on this turn.</p>

                  <p v-if="m.traceId" class="muted small mono trace">trace {{ m.traceId }}</p>
                </div>
              </Transition>
            </div>
          </div>
        </TransitionGroup>

        <Transition name="fade-slide">
          <div v-if="busy" class="thinking">
            <span class="typing"><i /><i /><i /></span>
            <span class="muted small">Running the specialists…</span>
          </div>
        </Transition>
      </div>

      <!-- Prompts and the composer share one footer so they scroll together as
           a block and never overlap the conversation. -->
      <div class="foot">
        <Transition name="pop">
          <CatchUpCard
            v-if="catchup"
            :summary="catchup.summary"
            :days-since="catchup.days_since"
            :busy="catchupBusy"
            @update="updateCatchup"
            @dismiss="dismissCatchup"
          />
        </Transition>

        <Transition name="pop">
          <ReviewCard
            v-if="reviewPrompt"
            :location="reviewPrompt.location"
            :busy="reviewBusy"
            @submit="submitReview"
            @dismiss="reviewPrompt = null"
          />
        </Transition>

        <div v-if="error" class="error">{{ error }}</div>

        <form class="compose" @submit.prevent="send()">
          <textarea
            ref="composer"
            v-model="draft"
            rows="1"
            :disabled="busy"
            placeholder="Where next?"
            aria-label="Message"
            @input="resizeComposer"
            @keydown="onComposerKey"
          />
          <button
            v-if="reportBug"
            class="bug"
            type="button"
            title="Report a bug"
            aria-label="Report a bug"
            @click="reportBug"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="8" y="7" width="8" height="12" rx="4" />
              <path d="M8 11H4.5M8 15H5M16 11h3.5M16 15h3M9.5 7 8 4.5M14.5 7 16 4.5M10 19.5 8.5 21.5M14 19.5l1.5 2" />
            </svg>
          </button>
          <button
            class="primary send"
            :disabled="busy || !draft.trim()"
            type="submit"
            aria-label="Send"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M4.5 12h13M12 5.5l6 6.5-6 6.5" />
            </svg>
          </button>
        </form>
      </div>
    </section>

    <!-- Desktop: a persistent, collapsible rail. The toggle lives in the
         sidebar's own sticky toolbar (see MemorySidebar), so collapsing never
         adds height on top of the panel's own viewport-bounded max-height. -->
    <aside class="rail hide-narrow" :class="{ collapsed: !railOpen }">
      <MemorySidebar :profile="profile" :collapsed="!railOpen">
        <template #toolbar>
          <button
            class="rail-toggle"
            type="button"
            :aria-expanded="railOpen"
            :aria-label="railOpen ? 'Hide trip panel' : 'Show trip panel'"
            :title="railOpen ? 'Hide trip panel' : 'Show trip panel'"
            @click="railOpen = !railOpen"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M14 6l-6 6 6 6" />
            </svg>
          </button>
        </template>
        <TripPanel
          :history="travelHistory"
          :wishlist="wishlist"
          :interests="interests"
          :key-interests="keyInterests"
          @drop-wishlist="dropWishlistItem"
        />
      </MemorySidebar>
    </aside>

    <!-- Mobile: the same content, one tap away. -->
    <BottomSheet :open="sheetOpen" title="Your trip" @close="sheetOpen = false">
      <MemorySidebar :profile="profile" flat>
        <TripPanel
          :history="travelHistory"
          :wishlist="wishlist"
          :interests="interests"
          :key-interests="keyInterests"
          @drop-wishlist="dropWishlistItem"
        />
      </MemorySidebar>
    </BottomSheet>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  gap: var(--sp-5);
  width: 100%;
  max-width: var(--container-wide);
  margin: 0 auto;
  align-items: start;
}

.chat {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  height: calc(var(--view-h) - 2 * var(--gutter));
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

/* On a phone the conversation takes the whole screen between the header and
   the tab bar: the page gutter is cancelled with negative margins so the chat
   runs edge to edge, which is both more room and more familiar. */
@media (max-width: 900px) {
  .layout { gap: 0; }
  .chat {
    height: var(--view-h);
    margin: calc(-1 * var(--gutter)) calc(-1 * max(var(--gutter), var(--safe-l))) calc(-1 * var(--gutter));
    border-radius: 0;
    border-left: none;
    border-right: none;
    border-top: none;
    box-shadow: none;
  }
}

/* -------------------------------------------------------- mobile context bar */
.context-bar {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex: none;
  width: 100%;
  text-align: left;
  padding: 10px max(var(--sp-4), var(--safe-l));
  border: none;
  border-bottom: 1px solid var(--line);
  border-radius: 0;
  background: color-mix(in srgb, var(--panel-2) 60%, transparent);
}
.context-bar:hover:not(:disabled) { transform: none; background: var(--panel-2); }
.ctx-label {
  font-size: var(--fs-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: var(--accent-bright);
  flex: none;
}
.ctx-summary {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-sm);
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ctx-chev { color: var(--muted); font-size: 18px; line-height: 1; flex: none; }

/* -------------------------------------------------------------- the stream */
.stream {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  padding: var(--sp-5) clamp(var(--sp-3), 2.4vw, var(--sp-6));
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}
.stream-inner { display: flex; flex-direction: column; gap: var(--sp-4); }

/* --------------------------------------------------------------- the intro */
.intro {
  margin: auto 0;
  text-align: center;
  padding: var(--sp-5) var(--sp-2);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-2);
}
.intro-mark {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: var(--radius);
  font-size: 24px;
  color: var(--on-accent);
  background: var(--accent-grad);
  box-shadow: var(--glow-accent);
  margin-bottom: var(--sp-2);
}
.intro h2 { margin: 0; font-size: clamp(20px, 5vw, 25px); }
.intro p { margin: 0; max-width: 46ch; font-size: 14.5px; color: var(--muted); }

/* -------------------------------------------------------------- the bubbles */
.msg.user { display: flex; justify-content: flex-end; }

.bubble {
  padding: 11px 15px;
  border-radius: var(--radius);
  max-width: min(90%, 68ch);
}
/* The user's own typed message stays literal plain text - pre-wrap so their own
   line breaks survive, and no markdown rendering (it is not the LLM's output). */
.bubble.user {
  background: var(--moss-grad);
  color: var(--text);
  border-bottom-right-radius: var(--radius-xs);
  white-space: pre-wrap;
  box-shadow: var(--glow-moss);
}
/* The assistant bubble renders real markdown (see components/Markdown.vue), so
   spacing comes from its own paragraph/list styles rather than pre-wrap. */
.bubble.assistant {
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-bottom-left-radius: var(--radius-xs);
}

.assistant-block { display: flex; flex-direction: column; gap: var(--sp-3); align-items: flex-start; width: 100%; }

.cards { --min: 250px; width: 100%; gap: var(--sp-3); }

/* ------------------------------------------------------------- the detail */
.detail-toggle {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--muted);
  font-size: 12.5px;
  padding: 5px 11px;
  border-radius: var(--radius-pill);
  border-color: var(--line);
}
.detail-toggle:hover:not(:disabled) { color: var(--text); }
.chev { display: inline-block; transition: transform var(--dur) var(--ease-out); font-size: 14px; line-height: 1; }
.chev.open { transform: rotate(90deg); }

.detail {
  width: 100%;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: var(--sp-3) var(--sp-4);
}
.detail .eyebrow { margin-top: var(--sp-3); }
.detail .eyebrow:first-child { margin-top: 0; }
.detail ul { margin: 0; padding: 0; list-style: none; }
.detail li { display: flex; flex-wrap: wrap; gap: var(--sp-2); align-items: center; margin-bottom: 5px; font-size: var(--fs-sm); }
.summary { flex-basis: 100%; }
.trace { margin: var(--sp-3) 0 0; }

/* ------------------------------------------------------------- the thinking */
.thinking { padding: 2px; display: flex; align-items: center; gap: 10px; }
.typing { display: inline-flex; gap: 3px; }
.typing i {
  display: inline-block;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--accent);
  animation: bounce 1.1s ease-in-out infinite;
}
.typing i:nth-child(2) { animation-delay: .15s; }
.typing i:nth-child(3) { animation-delay: .3s; }

/* ---------------------------------------------------------------- the foot */
.foot {
  flex: none;
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  padding: var(--sp-3) clamp(var(--sp-3), 2.4vw, var(--sp-5));
  border-top: 1px solid var(--line);
  background: color-mix(in srgb, var(--panel) 90%, transparent);
}

/* The placeholder is deliberately short. "Where should I go next?" wrapped to
   a second line inside a one-row box at 320px and got clipped mid-word once the
   report button took its share of the row. */
.compose { display: flex; gap: var(--sp-2); align-items: flex-end; }
.compose textarea {
  flex: 1;
  min-height: 46px;
  max-height: 132px;
  resize: none;
  overflow-y: auto;
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  line-height: 1.45;
}
.send {
  flex: none;
  width: 46px;
  height: 46px;
  padding: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
}
.send svg { width: 20px; height: 20px; }

/* Secondary to Send, but it still has to read as a button. Borderless and
   --muted, it disappeared into the dark composer bar entirely - which defeats
   the point of moving it here. It gets the same outline treatment as the text
   box so it is unmistakably a control, while the colour keeps Send the
   brightest thing in the row. */
.bug {
  flex: none;
  width: 42px;
  height: 42px;
  margin-bottom: 2px;
  padding: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: var(--stone-300);
  background: var(--bg);
  border: 1px solid var(--line);
}
.bug svg { width: 19px; height: 19px; }
.bug:hover:not(:disabled) {
  color: var(--accent-bright);
  background: var(--accent-soft);
  border-color: var(--accent);
}

/* At 320px the two buttons plus a usable text box is a genuine squeeze, so the
   bug button loses a few pixels rather than the composer. */
@media (max-width: 380px) {
  .bug { width: 36px; height: 36px; margin-bottom: 5px; }
  .bug svg { width: 17px; height: 17px; }
}

/* ---------------------------------------------------------------- the rail */
/* flex-basis (not width) is what animates: shrinking it back also lets .chat's
   flex: 1 1 auto claim the reclaimed space in the same motion, so the column
   genuinely narrows rather than leaving a collapsed box in reserved space.
   The rail itself is just the sticky positioner - its child (MemorySidebar's
   own panel) owns the height cap, the internal scroll, and the sticky toolbar
   the toggle button lives in, so collapsing never adds height above it. */
.rail {
  flex: 0 1 350px;
  min-width: 290px;
  position: sticky;
  top: calc(var(--header-h) + var(--gutter));
  transition: flex-basis var(--dur-slow) var(--ease-out), min-width var(--dur-slow) var(--ease-out);
}
.rail.collapsed {
  flex-basis: 52px;
  min-width: 52px;
}

.rail-toggle {
  flex: none;
  width: 30px;
  height: 30px;
  padding: 0;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: var(--muted);
  background: transparent;
  border: 1px solid var(--line);
  transition: color var(--dur-fast) ease, border-color var(--dur-fast) ease, background var(--dur-fast) ease;
}
.rail-toggle:hover:not(:disabled) { color: var(--text); border-color: var(--stone-500); background: var(--panel-2); transform: none; }
.rail-toggle svg { width: 15px; height: 15px; transition: transform var(--dur-slow) var(--ease-out); }
.rail.collapsed .rail-toggle svg { transform: rotate(180deg); }
</style>
