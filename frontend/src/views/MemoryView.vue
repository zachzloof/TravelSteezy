<script setup>
// The memory debug page: read everything, delete anything.
//
// Different purpose from My Preferences, which is "edit your own trip
// profile" for everyday use. This is "show me exactly what is in the
// database and exactly what gets fed into the next agent prompt" - built
// because that visibility turned out to be necessary for debugging, not just
// nice to have. Every section here reads real rows through GET /memory/me;
// nothing is summarised or reconstructed client-side.
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, session, tokens } from '../api'
import { labelFor } from '../preferences'

const router = useRouter()

const data = ref(null)
const loading = ref(true)
const error = ref('')
const notice = ref('')
const busy = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.getMemoryDebug()
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      tokens.clearUser()
      router.push('/login')
      return
    }
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function act(fn, message) {
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    data.value = await fn()
    notice.value = message
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

const clearField = (field) =>
  act(() => api.clearMemoryProfileField(field), `Cleared ${field}.`)
const removeInterest = (interest) =>
  act(() => api.deleteMemoryInterest(interest), `Removed "${interest}".`)
const removePassport = (country) =>
  act(() => api.deleteMemoryPassport(country), `Removed ${country}.`)
const removeStop = (location) =>
  act(() => api.removeStop(location), `Removed ${location} from the route.`)
const dropWish = (location) =>
  act(() => api.dropWishlist(location), `Dropped ${location}.`)

async function resetOnboarding() {
  if (!confirm('Send this account back through the welcome page questions? The route, wishlist and interests are kept.')) return
  await act(() => api.resetOnboardingDebug(), 'Onboarding reset - the welcome page starts at question one again.')
  session.reset()
}

async function forgetEverything() {
  if (!confirm('Erase EVERYTHING this account remembers - profile, route, wishlist, interests, onboarding, audit log? This cannot be undone.')) return
  busy.value = true
  error.value = ''
  try {
    await api.forgetMe()
    session.reset()
    notice.value = 'Wiped. Reloading...'
    await load()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

// Profile fields worth a row and a clear button. Deprecated columns
// (trip_start_date/trip_end_date) are shown too, greyed, so "is this really
// dead" is answered by looking rather than trusting a claim.
const PROFILE_ROWS = [
  ['nationality', 'nationality (mirrors primary passport)'],
  ['current_location', 'current_location'],
  ['budget_band', 'budget_band'],
  ['travel_style', 'travel_style'],
  ['climate_preference', 'climate_preference'],
  ['social_style', 'social_style'],
  ['visa_deadline_date', 'visa_deadline_date'],
  ['visa_deadline_note', 'visa_deadline_note'],
  ['interests', 'interests (free-text mirror)'],
  ['onboarded', 'onboarded'],
  ['updated_at', 'updated_at'],
]
const DEPRECATED_ROWS = [
  ['trip_start_date', 'trip_start_date'],
  ['trip_end_date', 'trip_end_date'],
]
</script>

<template>
  <div class="wrap">
    <header class="top">
      <div>
        <h1>Memory</h1>
        <p class="muted small intro">
          Everything this account's memory actually contains, and exactly what
          gets spliced into the next agent prompt. For debugging, and for anyone
          who wants the receipts rather than a summary.
        </p>
      </div>
    </header>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="notice" class="notice">{{ notice }}</div>
    <div v-if="loading" class="panel muted">Loading…</div>

    <template v-else-if="data">
      <!-- ======================================================= fed to prompts -->
      <section class="panel">
        <div class="panel-head">
          <h2>What gets fed into the next turn</h2>
          <p class="muted small">
            The EXACT text every agent reads, rendered live by the same two
            functions the real chat turn calls - not a paraphrase.
          </p>
        </div>
        <h4>memory_block (trip profile)</h4>
        <pre class="block">{{ data.memory_block }}</pre>
        <h4>travel_block (route, ratings, wishlist, interests)</h4>
        <pre class="block">{{ data.travel_block }}</pre>
      </section>

      <div class="lists">
        <!-- ================================================= raw profile row -->
        <section class="panel">
          <div class="panel-head">
            <h2>Trip profile (raw row)</h2>
            <p class="muted small">Every column, not just the ones the ordinary UI shows.</p>
          </div>
          <table class="kv">
            <tbody>
              <tr v-for="[key, label] in PROFILE_ROWS" :key="key">
                <td class="key">{{ label }}</td>
                <td class="val" :class="{ unset: !data.profile_row[key] }">
                  {{ data.profile_row[key] ?? '(null)' }}
                </td>
                <td class="op">
                  <button
                    v-if="data.profile_row[key]"
                    class="ghost small"
                    :disabled="busy"
                    @click="clearField(key)"
                  >clear</button>
                </td>
              </tr>
              <tr v-for="[key, label] in DEPRECATED_ROWS" :key="key" class="deprecated">
                <td class="key">{{ label }} <span class="tag">deprecated</span></td>
                <td class="val" :class="{ unset: !data.profile_row[key] }">
                  {{ data.profile_row[key] ?? '(null)' }}
                </td>
                <td class="op muted small">not read anywhere</td>
              </tr>
            </tbody>
          </table>

          <h4>Passports</h4>
          <ul v-if="data.passports.length" class="chips">
            <li v-for="p in data.passports" :key="p">
              <span>{{ p }}</span>
              <button class="ghost small" :disabled="busy" @click="removePassport(p)">×</button>
            </li>
          </ul>
          <p v-else class="muted small">None stored.</p>
        </section>

        <!-- ===================================================== onboarding -->
        <section class="panel">
          <div class="panel-head">
            <h2>Onboarding state</h2>
          </div>
          <table class="kv">
            <tbody>
              <tr><td class="key">status</td><td class="val">{{ data.onboarding_state.status }}</td></tr>
              <tr><td class="key">step</td><td class="val">{{ data.onboarding_state.step }}</td></tr>
              <tr><td class="key">turns</td><td class="val">{{ data.onboarding_state.turns }}</td></tr>
              <tr>
                <td class="key">answered</td>
                <td class="val">{{ data.onboarding_state.answered.join(', ') || '(none)' }}</td>
              </tr>
            </tbody>
          </table>
          <button class="ghost small" :disabled="busy" @click="resetOnboarding">
            Reset onboarding (keep route/wishlist/interests)
          </button>
        </section>
      </div>

      <div class="lists">
        <!-- ======================================================= history -->
        <section class="panel">
          <div class="panel-head">
            <h2>Travel history (raw rows)</h2>
            <p class="muted small">{{ data.travel_history.length }} stop(s).</p>
          </div>
          <div class="scroll">
            <table v-if="data.travel_history.length" class="raw">
              <thead>
                <tr>
                  <th>#</th><th>location</th><th>type</th><th>country</th><th>source</th>
                  <th>rating</th><th>notes</th><th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="h in data.travel_history" :key="h.id">
                  <td>{{ h.order_index }}</td>
                  <td>{{ h.location }}</td>
                  <td class="muted">{{ h.location_type }}</td>
                  <td class="muted">{{ h.country || '—' }}</td>
                  <td class="muted">{{ h.source }}</td>
                  <td>{{ h.rating ?? '—' }}</td>
                  <td class="notes">{{ h.review_notes || '—' }}</td>
                  <td><button class="ghost small" :disabled="busy" @click="removeStop(h.location)">delete</button></td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted small">Nothing stored.</p>
          </div>
        </section>

        <!-- ======================================================= wishlist -->
        <section class="panel">
          <div class="panel-head">
            <h2>Wishlist (raw rows, all statuses)</h2>
          </div>
          <div class="scroll">
            <table v-if="data.wishlist.length" class="raw">
              <thead>
                <tr><th>location</th><th>priority</th><th>status</th><th>source</th><th></th></tr>
              </thead>
              <tbody>
                <tr v-for="w in data.wishlist" :key="w.id">
                  <td>{{ w.location }}</td>
                  <td>{{ w.priority }}</td>
                  <td class="muted">{{ w.status }}</td>
                  <td class="muted">{{ w.source }}</td>
                  <td>
                    <button
                      v-if="w.status === 'open'"
                      class="ghost small"
                      :disabled="busy"
                      @click="dropWish(w.location)"
                    >drop</button>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted small">Nothing stored.</p>
          </div>
        </section>
      </div>

      <div class="lists">
        <!-- ====================================================== interests -->
        <section class="panel">
          <div class="panel-head">
            <h2>Interests (with weight)</h2>
            <p class="muted small">Weight increments each time onboarding or chat mentions it again.</p>
          </div>
          <table v-if="data.interests.length" class="raw">
            <thead><tr><th>interest</th><th>weight</th><th></th></tr></thead>
            <tbody>
              <tr v-for="i in data.interests" :key="i.interest">
                <td>{{ i.interest }}</td>
                <td>{{ i.weight }}</td>
                <td><button class="ghost small" :disabled="busy" @click="removeInterest(i.interest)">delete</button></td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted small">None stored.</p>
        </section>

        <!-- ============================================ recommendation feedback -->
        <section class="panel">
          <div class="panel-head">
            <h2>Recommendation feedback</h2>
            <p class="muted small">Whether a surfaced suggestion was accepted or dropped. Feeds the RAG loop below.</p>
          </div>
          <table v-if="data.recommendation_feedback.length" class="raw">
            <thead><tr><th>location</th><th>from</th><th>verdict</th><th>when</th></tr></thead>
            <tbody>
              <tr v-for="(f, i) in data.recommendation_feedback" :key="i">
                <td>{{ f.location }}</td>
                <td class="muted">{{ f.from_location || '—' }}</td>
                <td>{{ f.verdict }}</td>
                <td class="muted small">{{ f.created_at }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted small">None recorded.</p>
        </section>
      </div>

      <!-- ============================================== published experience -->
      <section class="panel">
        <div class="panel-head">
          <h2>Published to other travellers</h2>
          <p class="muted small">
            Fetched by id from the shared RAG experience store - this is what is
            actually out there, not what was submitted. A review kept private, or
            too short to index, correctly will not appear.
          </p>
        </div>
        <ul v-if="data.published_experience_documents.length" class="published">
          <li v-for="d in data.published_experience_documents" :key="d.id">
            <span class="mono id">{{ d.id }}</span>
            <span class="text">{{ d.text || d.metadata?.text }}</span>
          </li>
        </ul>
        <p v-else class="muted small">Nothing of yours is currently published.</p>
      </section>

      <!-- ==================================================== turns + audit -->
      <div class="lists">
        <section class="panel">
          <div class="panel-head">
            <h2>Conversation scrollback</h2>
            <p class="muted small">
              Stored, capped, and shown here - but NOT fed into any agent prompt.
              This app's memory is the structured data above, not chat replay.
            </p>
          </div>
          <ul v-if="data.conversation_turns.length" class="turns">
            <li v-for="(t, i) in data.conversation_turns" :key="i">
              <span class="tag">{{ t.role }}</span>
              <span class="text">{{ t.content }}</span>
            </li>
          </ul>
          <p v-else class="muted small">Nothing stored.</p>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2>Memory writes (audit log)</h2>
            <p class="muted small">Every write, agent-inferred or your own edit. Up to 200 shown.</p>
          </div>
          <ul v-if="data.memory_writes.length" class="writes">
            <li v-for="(w, i) in data.memory_writes" :key="i">
              <span class="mono op">{{ w.operation }}</span>
              <span class="tag">{{ w.source }}</span>
              <span class="muted small">{{ w.created_at }}</span>
              <div class="muted small payload">
                {{ Object.entries(w.payload).map(([k, v]) => `${k}=${v}`).join(', ') || '—' }}
              </div>
            </li>
          </ul>
          <p v-else class="muted small">No writes yet.</p>
        </section>
      </div>

      <!-- ========================================================= danger -->
      <section class="panel danger">
        <h2>Forget everything</h2>
        <p class="muted small">
          Wipes the profile, passports, route, wishlist, interests, onboarding
          state and this account's own audit log. Cannot be undone.
        </p>
        <button class="danger" :disabled="busy" @click="forgetEverything">Forget everything</button>
      </section>
    </template>
  </div>
</template>

<style scoped>
.wrap { max-width: var(--container-wide); margin: 0 auto; display: flex; flex-direction: column; gap: 18px; }
.top h1 { margin: 0 0 4px; font-size: 22px; }
.intro { margin: 0; max-width: 640px; }

.panel-head { margin-bottom: 14px; }
.panel-head h2 { margin: 0 0 3px; font-size: 15.5px; }
.panel-head p { margin: 0; }

h4 { margin: 14px 0 6px; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }
h4:first-of-type { margin-top: 0; }

.block {
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px 14px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12.5px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.lists { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; align-items: start; }
@media (max-width: 860px) { .lists { grid-template-columns: 1fr; } }

.kv { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 6px; }
.kv td { padding: 5px 6px; border-bottom: 1px solid var(--line); vertical-align: top; }
.kv .key { color: var(--muted); width: 46%; }
.kv .val { word-break: break-word; }
.kv .val.unset { color: var(--muted-2); font-style: italic; }
.kv .op { width: 60px; text-align: right; }
.kv tr.deprecated .key, .kv tr.deprecated .val { opacity: .6; }

.scroll { overflow-x: auto; }
table.raw { width: 100%; border-collapse: collapse; font-size: 12.5px; }
table.raw th {
  text-align: left; padding: 5px 8px; color: var(--muted); font-weight: 500;
  border-bottom: 1px solid var(--line); white-space: nowrap;
}
table.raw td { padding: 5px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
table.raw .notes { max-width: 220px; word-break: break-word; }

.chips { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 6px; }
.chips li {
  display: flex; align-items: center; gap: 6px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 999px;
  padding: 3px 5px 3px 10px; font-size: 13px;
}
.chips button { padding: 0 6px; border: none; background: none; color: var(--muted); font-size: 15px; }
.chips button:hover { color: var(--bad); }

.published { list-style: none; margin: 0; padding: 0; }
.published li { display: flex; flex-direction: column; gap: 2px; padding: 8px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
.published li:last-child { border-bottom: none; }
.published .id { font-size: 11px; color: var(--accent); }

.turns { list-style: none; margin: 0; padding: 0; max-height: 320px; overflow-y: auto; }
.turns li { display: flex; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
.turns li:last-child { border-bottom: none; }
.turns .text { word-break: break-word; }

.writes { list-style: none; margin: 0; padding: 0; max-height: 320px; overflow-y: auto; }
.writes li { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 7px 0; border-bottom: 1px solid var(--line); }
.writes li:last-child { border-bottom: none; }
.op { font-size: 11.5px; color: var(--accent); }
.payload { flex-basis: 100%; }

.danger { border-color: var(--bad-dim); }
.danger h2 { margin: 0 0 6px; font-size: 15.5px; }
</style>
