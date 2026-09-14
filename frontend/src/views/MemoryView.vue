<script setup>
// The memory debug page: read everything, delete anything.
//
// Different purpose from the Trip page, which is "edit your own trip profile"
// for everyday use. This is "show me exactly what is in the database and
// exactly what gets fed into the next agent prompt" - built because that
// visibility turned out to be necessary for debugging, not just nice to have.
// Every section here reads real rows through GET /memory/me; nothing is
// summarised or reconstructed client-side.
//
// It is eleven panels of raw data, so it is split into four tabs. On a phone
// the tables restack as labelled cards (see the media query at the bottom)
// rather than scrolling sideways - a seven-column row is not readable at
// 390px no matter how much you let it overflow.
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, session, tokens } from '../api'
import SegmentedTabs from '../components/SegmentedTabs.vue'

const router = useRouter()

const data = ref(null)
const loading = ref(true)
const error = ref('')
const notice = ref('')
const busy = ref(false)
const tab = ref('prompt')

const TABS = [
  { id: 'prompt', label: 'Prompt' },
  { id: 'profile', label: 'Profile' },
  { id: 'trip', label: 'Trip' },
  { id: 'activity', label: 'Activity' }
]

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

const onboardingRows = computed(() => {
  const s = data.value?.onboarding_state
  if (!s) return []
  return [
    ['status', s.status],
    ['step', s.step],
    ['turns', s.turns],
    ['answered', s.answered.join(', ') || '(none)']
  ]
})
</script>

<template>
  <div class="page wide">
    <header class="page-head">
      <div>
        <h1 class="grad-text cool">Memory</h1>
        <p class="muted small">
          Everything this account's memory actually contains, and exactly what
          gets spliced into the next agent prompt. For debugging, and for anyone
          who wants the receipts rather than a summary.
        </p>
      </div>
    </header>

    <SegmentedTabs v-if="data" v-model="tab" :tabs="TABS" label="Memory sections" />

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="notice" class="notice">{{ notice }}</div>

    <div v-if="loading" class="panel">
      <div class="skeleton line" />
      <div class="skeleton line short" />
      <div class="skeleton line" />
    </div>

    <template v-else-if="data">
      <!-- ================================================== 1. prompt -->
      <section v-show="tab === 'prompt'" class="panel">
        <div class="panel-head">
          <h2>What gets fed into the next turn</h2>
          <p class="muted small">
            The EXACT text every agent reads, rendered live by the same two
            functions the real chat turn calls - not a paraphrase.
          </p>
        </div>
        <p class="eyebrow">memory_block (trip profile)</p>
        <pre class="block">{{ data.memory_block }}</pre>
        <p class="eyebrow spaced">travel_block (route, ratings, wishlist, interests)</p>
        <pre class="block">{{ data.travel_block }}</pre>
      </section>

      <!-- ================================================= 2. profile -->
      <template v-if="tab === 'profile'">
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
                <td class="op muted small">unused</td>
              </tr>
            </tbody>
          </table>

          <p class="eyebrow spaced">Passports</p>
          <ul v-if="data.passports.length" class="chips">
            <li v-for="p in data.passports" :key="p">
              <span>{{ p }}</span>
              <button class="icon-btn destructive" :disabled="busy" :aria-label="`Remove ${p}`" @click="removePassport(p)">×</button>
            </li>
          </ul>
          <p v-else class="muted small">None stored.</p>
        </section>

        <section class="panel">
          <div class="panel-head"><h2>Onboarding state</h2></div>
          <table class="kv">
            <tbody>
              <tr v-for="[k, v] in onboardingRows" :key="k">
                <td class="key">{{ k }}</td>
                <td class="val" colspan="2">{{ v }}</td>
              </tr>
            </tbody>
          </table>
          <button class="small" :disabled="busy" @click="resetOnboarding">
            Reset onboarding (keep route/wishlist/interests)
          </button>
        </section>

        <section class="panel danger">
          <div class="panel-head">
            <h2>Forget everything</h2>
            <p class="muted small">
              Wipes the profile, passports, route, wishlist, interests, onboarding
              state and this account's own audit log. Cannot be undone.
            </p>
          </div>
          <button class="danger" :disabled="busy" @click="forgetEverything">Forget everything</button>
        </section>
      </template>

      <!-- ==================================================== 3. trip -->
      <template v-if="tab === 'trip'">
        <section class="panel">
          <div class="panel-head">
            <h2>Travel history (raw rows)</h2>
            <p class="muted small">{{ data.travel_history.length }} stop(s).</p>
          </div>
          <table v-if="data.travel_history.length" class="raw">
            <thead>
              <tr>
                <th>#</th><th>location</th><th>type</th><th>country</th><th>source</th>
                <th>rating</th><th>notes</th><th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="h in data.travel_history" :key="h.id">
                <td data-label="#">{{ h.order_index }}</td>
                <td data-label="location">{{ h.location }}</td>
                <td data-label="type" class="muted">{{ h.location_type }}</td>
                <td data-label="country" class="muted">{{ h.country || '—' }}</td>
                <td data-label="source" class="muted">{{ h.source }}</td>
                <td data-label="rating">{{ h.rating ?? '—' }}</td>
                <td data-label="notes" class="notes">{{ h.review_notes || '—' }}</td>
                <td class="op"><button class="ghost small" :disabled="busy" @click="removeStop(h.location)">delete</button></td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted small">Nothing stored.</p>
        </section>

        <section class="panel">
          <div class="panel-head"><h2>Wishlist (raw rows, all statuses)</h2></div>
          <table v-if="data.wishlist.length" class="raw">
            <thead>
              <tr><th>location</th><th>priority</th><th>status</th><th>source</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="w in data.wishlist" :key="w.id">
                <td data-label="location">{{ w.location }}</td>
                <td data-label="priority">{{ w.priority }}</td>
                <td data-label="status" class="muted">{{ w.status }}</td>
                <td data-label="source" class="muted">{{ w.source }}</td>
                <td class="op">
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
        </section>

        <div class="two-col">
          <section class="panel">
            <div class="panel-head">
              <h2>Interests (with weight)</h2>
              <p class="muted small">Weight increments each time onboarding or chat mentions it again.</p>
            </div>
            <table v-if="data.interests.length" class="raw">
              <thead><tr><th>interest</th><th>weight</th><th></th></tr></thead>
              <tbody>
                <tr v-for="i in data.interests" :key="i.interest">
                  <td data-label="interest">{{ i.interest }}</td>
                  <td data-label="weight">{{ i.weight }}</td>
                  <td class="op"><button class="ghost small" :disabled="busy" @click="removeInterest(i.interest)">delete</button></td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted small">None stored.</p>
          </section>

          <section class="panel">
            <div class="panel-head">
              <h2>Recommendation feedback</h2>
              <p class="muted small">Whether a surfaced suggestion was accepted or dropped. Feeds the RAG loop.</p>
            </div>
            <table v-if="data.recommendation_feedback.length" class="raw">
              <thead><tr><th>location</th><th>from</th><th>verdict</th><th>when</th></tr></thead>
              <tbody>
                <tr v-for="(f, i) in data.recommendation_feedback" :key="i">
                  <td data-label="location">{{ f.location }}</td>
                  <td data-label="from" class="muted">{{ f.from_location || '—' }}</td>
                  <td data-label="verdict">{{ f.verdict }}</td>
                  <td data-label="when" class="muted small">{{ f.created_at }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="muted small">None recorded.</p>
          </section>
        </div>
      </template>

      <!-- ================================================ 4. activity -->
      <template v-if="tab === 'activity'">
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

        <div class="two-col">
          <section class="panel">
            <div class="panel-head">
              <h2>Conversation scrollback</h2>
              <p class="muted small">
                Stored, capped, and shown here - but NOT fed into any agent prompt.
                This app's memory is the structured data above, not chat replay.
              </p>
            </div>
            <ul v-if="data.conversation_turns.length" class="turns feed">
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
            <ul v-if="data.memory_writes.length" class="writes feed">
              <li v-for="(w, i) in data.memory_writes" :key="i">
                <div class="cluster">
                  <span class="mono op">{{ w.operation }}</span>
                  <span class="tag">{{ w.source }}</span>
                  <span class="muted small">{{ w.created_at }}</span>
                </div>
                <div class="muted small payload">
                  {{ Object.entries(w.payload).map(([k, v]) => `${k}=${v}`).join(', ') || '—' }}
                </div>
              </li>
            </ul>
            <p v-else class="muted small">No writes yet.</p>
          </section>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.panel-head h2 { font-size: var(--fs-h2); }

.skeleton.line { height: 14px; margin-bottom: 10px; }
.skeleton.line.short { width: 55%; }

.eyebrow.spaced { margin-top: var(--sp-4); }

.block {
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: var(--sp-3) var(--sp-4);
  font-family: var(--font-mono);
  font-size: 12.5px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

/* ------------------------------------------------------------ key / value */
.kv { width: 100%; border-collapse: collapse; font-size: var(--fs-sm); margin-bottom: var(--sp-3); }
.kv td { padding: 7px 6px; border-bottom: 1px solid var(--line); vertical-align: top; }
.kv tr:last-child td { border-bottom: none; }
.kv .key { color: var(--muted); width: 45%; font-family: var(--font-mono); font-size: 12px; }
.kv .val { word-break: break-word; }
.kv .val.unset { color: var(--muted-2); font-style: italic; }
.kv .op { width: 62px; text-align: right; white-space: nowrap; }
.kv tr.deprecated .key, .kv tr.deprecated .val { opacity: .55; }

/* ----------------------------------------------------------- raw row table */
table.raw { width: 100%; border-collapse: collapse; font-size: 12.5px; }
table.raw th {
  text-align: left; padding: 6px 8px; color: var(--muted); font-weight: 600;
  font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: .04em;
  border-bottom: 1px solid var(--line); white-space: nowrap;
}
table.raw td { padding: 7px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
table.raw tbody tr:last-child td { border-bottom: none; }
table.raw tbody tr { transition: background-color var(--dur-fast) ease; }
@media (hover: hover) { table.raw tbody tr:hover { background-color: var(--panel-2); } }
table.raw .notes { max-width: 220px; word-break: break-word; }
table.raw .op { text-align: right; white-space: nowrap; }

/* A wide raw table cannot be made to fit a phone, so below 760px each row
   becomes its own labelled card. The column headers are hidden and every cell
   carries its own label from data-label, which is why the markup sets it. */
@media (max-width: 760px) {
  table.raw thead { display: none; }
  table.raw, table.raw tbody, table.raw tr, table.raw td { display: block; width: 100%; }
  table.raw tr {
    border: 1px solid var(--line);
    border-radius: var(--radius-sm);
    padding: var(--sp-3);
    margin-bottom: var(--sp-2);
    background: var(--bg);
  }
  table.raw td { border: none; padding: 2px 0; display: flex; gap: var(--sp-3); align-items: baseline; }
  table.raw td::before {
    content: attr(data-label);
    flex: none;
    width: 78px;
    color: var(--muted);
    font-size: var(--fs-xs);
    text-transform: uppercase;
    letter-spacing: .04em;
  }
  table.raw td.op { justify-content: flex-end; padding-top: var(--sp-2); }
  table.raw .notes { max-width: none; }

  .kv .key { width: 42%; }
}

/* ------------------------------------------------------------------ chips */
.chips { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 6px; }
.chips li {
  display: flex; align-items: center; gap: var(--sp-1);
  background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius-pill);
  padding: 3px 5px 3px 12px; font-size: var(--fs-sm);
}
.chips .icon-btn { width: 24px; height: 24px; font-size: 15px; }

/* ------------------------------------------------------------------ feeds */
.published, .turns, .writes { list-style: none; margin: 0; padding: 0; }
.published li { display: flex; flex-direction: column; gap: 2px; padding: var(--sp-2) 0; border-bottom: 1px solid var(--line); font-size: var(--fs-sm); }
.published li:last-child { border-bottom: none; }
.published .id { font-size: var(--fs-xs); color: var(--accent); word-break: break-all; }

/* A capped, independently scrolling feed keeps a 200-row audit log from
   burying every panel under it. */
.feed { max-height: 340px; overflow-y: auto; overscroll-behavior: contain; }
.turns li { display: flex; gap: var(--sp-2); padding: 7px 0; border-bottom: 1px solid var(--line); font-size: var(--fs-sm); }
.turns li:last-child { border-bottom: none; }
.turns .text { word-break: break-word; }

.writes li { padding: 8px 0; border-bottom: 1px solid var(--line); }
.writes li:last-child { border-bottom: none; }
.op { font-size: 11.5px; color: var(--accent); }
.payload { margin-top: 2px; word-break: break-word; }

.danger { border-color: var(--bad-dim); }
</style>
