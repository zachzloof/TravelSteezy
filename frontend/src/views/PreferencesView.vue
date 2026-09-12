<script setup>
// The trip profile, as three independent panels rather than one long form.
//
// The old version was a single "Trip profile" form with everything in it, plus
// two sidebar boxes, and the route and wishlist were not editable here at all -
// they could only be seen in the chat sidebar and only changed by talking to an
// agent. That is backwards: this is the user's own data.
//
// The three panels map onto three genuinely different questions:
//
//   About you  - who you are and how you travel. A form: edit, then save.
//   History    - where you have been, and what you thought of it. The ratings
//                here are read before every recommendation, which is why they
//                are one tap and always editable.
//   Wishlist   - where you want to go. Somewhere you have already been is
//                allowed: wanting a second go at a place is a real preference.
//
// History and wishlist actions persist immediately, because each one is a
// discrete action rather than an edit-in-progress. Only the About You form has a
// Save button, because that is the only panel where you are mid-thought.
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, tokens } from '../api'
import {
  BUDGET_BANDS,
  CLIMATE_PREFS,
  PRIORITIES,
  SOCIAL_STYLES,
  TRAVEL_STYLES
} from '../preferences'
import ScalePicker from '../components/ScalePicker.vue'
import StarRating from '../components/StarRating.vue'
import TagInput from '../components/TagInput.vue'

const router = useRouter()

const INTEREST_SUGGESTIONS = [
  'nature', 'food', 'trekking', 'diving', 'beaches', 'history',
  'nightlife', 'culture', 'markets', 'wildlife', 'surfing', 'photography'
]

const form = ref({
  passports: [],
  current_location: '',
  budget_band: '',
  travel_style: '',
  climate_preference: '',
  social_style: '',
  trip_start_date: '',
  trip_end_date: '',
  visa_deadline_date: '',
  visa_deadline_note: ''
})

const history = ref([])
const wishlist = ref([])
const interests = ref([])
const writes = ref([])
const visited = ref([])

const newStop = ref({ location: '', country: '' })
const newWish = ref({ location: '', priority: 2 })
const departure = ref({ country: '', departure_date: '' })

const busy = ref(false)
const error = ref('')
const saved = ref('')
const showWrites = ref(false)

// Newest first: the stop you just left is the one you are most likely to rate.
const route = computed(() => [...history.value].slice().reverse())
const rated = computed(() => history.value.filter((h) => h.rating).length)

onMounted(async () => {
  await Promise.all([loadProfile(), loadTravel()])
})

async function loadProfile() {
  try {
    applyProfile(await api.getProfile())
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      tokens.clearUser()
      router.push('/login')
    } else {
      error.value = e.message
    }
  }
}

async function loadTravel() {
  try {
    applyTravel(await api.getTravel())
  } catch (e) {
    error.value = e.message
  }
}

function applyProfile(res) {
  const profile = res.profile || {}
  for (const key of Object.keys(form.value)) {
    form.value[key] = key === 'passports' ? [...(profile.passports || [])] : profile[key] ?? ''
  }
  writes.value = res.recent_writes || []
  visited.value = res.visited_history || []
}

function applyTravel(res) {
  if (res.travel_history) history.value = res.travel_history
  if (res.wishlist) wishlist.value = res.wishlist
  if (res.interests) interests.value = res.interests
}

/** Run one mutating call, keeping the panels in sync and surfacing failures. */
async function act(fn, message = '') {
  error.value = ''
  saved.value = ''
  busy.value = true
  try {
    applyTravel(await fn())
    saved.value = message
    // The audit log and the mirrored interests text live on the profile side, so
    // a travel write has to refresh both or the two panels drift apart.
    applyProfile(await api.getProfile())
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

// ---------------------------------------------------------------- about you
async function saveProfile() {
  error.value = ''
  saved.value = ''
  busy.value = true
  try {
    // This panel renders every field it can write, so an empty control genuinely
    // means "I do not have one" rather than "this was not on screen" - which is
    // why it can safely ask for cleared fields to be blanked. `clear` names them
    // explicitly; the backend will not blank anything it was not told to.
    const patch = { passports: form.value.passports, clear: [] }
    for (const [key, value] of Object.entries(form.value)) {
      if (key === 'passports') continue
      if (value !== '' && value !== null) patch[key] = value
      else patch.clear.push(key)
    }
    applyProfile(await api.patchProfile(patch))
    saved.value = 'Saved. The assistant uses this on your next message.'
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function saveInterests(next) {
  interests.value = next
  await act(() => api.setInterests(next), 'Interests updated.')
}

// ------------------------------------------------------------------ history
function addStop() {
  const location = newStop.value.location.trim()
  if (!location) return
  const country = newStop.value.country.trim()
  newStop.value = { location: '', country: '' }
  return act(
    () => api.addVisit({ location, country: country || null }),
    `${location} added to your history.`
  )
}

function rateStop(stop, rating) {
  stop.rating = rating
  return act(() => api.rateStop(stop.location, rating), '')
}

function removeStop(location) {
  if (!confirm(`Remove ${location} from your travel history?`)) return
  return act(() => api.removeStop(location), `${location} removed.`)
}

function logDeparture() {
  const country = departure.value.country.trim()
  if (!country) return
  const departure_date = departure.value.departure_date || null
  departure.value = { country: '', departure_date: '' }
  error.value = ''
  busy.value = true
  return api
    .logDeparture({ country, departure_date })
    .then((res) => {
      applyProfile(res)
      saved.value = `${country} moved out of active context and into your history.`
      return loadTravel()
    })
    .catch((e) => {
      error.value = e.message
    })
    .finally(() => {
      busy.value = false
    })
}

// ----------------------------------------------------------------- wishlist
function addWish() {
  const location = newWish.value.location.trim()
  if (!location) return
  const priority = newWish.value.priority
  newWish.value = { location: '', priority: 2 }
  return act(
    () => api.addWishlist({ location, priority }),
    `${location} added to your wishlist.`
  )
}

function setPriority(item, priority) {
  return act(() => api.addWishlist({ location: item.location, priority }), '')
}

function dropWish(location) {
  return act(() => api.dropWishlist(location), `${location} dropped.`)
}

// -------------------------------------------------------------------- reset
async function forgetAll() {
  if (!confirm('Erase everything Travel Steezy remembers about your trip? Your account stays.')) return
  busy.value = true
  try {
    applyProfile(await api.forgetMe())
    await loadTravel()
    saved.value = 'Memory cleared for this account.'
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="wrap">
    <header class="top">
      <div>
        <h1>Your trip profile</h1>
        <p class="muted small intro">
          Every agent reads this before it answers, so you never have to repeat
          yourself. Change anything here and the next recommendation reflects it.
        </p>
      </div>
      <RouterLink class="ghost small redo" to="/welcome">Redo the questions</RouterLink>
    </header>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="saved" class="notice">{{ saved }}</div>

    <!-- ================================================== 1. about you -->
    <form class="panel" @submit.prevent="saveProfile">
      <div class="panel-head">
        <h2>About you</h2>
        <p class="muted small">Who you are and how you travel.</p>
      </div>

      <div class="two">
        <TagInput
          v-model="form.passports"
          label="Nationality / passports"
          hint="First one is your primary"
          placeholder="United Kingdom"
        />
        <div class="field">
          <label for="loc">Currently in</label>
          <input id="loc" v-model="form.current_location" placeholder="Chiang Mai" />
        </div>
      </div>
      <p class="muted small aside">
        Visa rules are nationality-specific, so list every passport you hold — the
        first is used for visa checks, and the rest are compared against it when
        one of them gives you an easier entry.
      </p>

      <div class="scales">
        <ScalePicker
          v-model="form.budget_band"
          label="Budget band"
          :options="BUDGET_BANDS"
        />
        <ScalePicker
          v-model="form.travel_style"
          label="Travel pace"
          :options="TRAVEL_STYLES"
        />
        <ScalePicker
          v-model="form.climate_preference"
          label="Climate preference"
          :options="CLIMATE_PREFS"
        />
        <ScalePicker
          v-model="form.social_style"
          label="Travelling"
          :options="SOCIAL_STYLES"
        />
      </div>

      <div class="sub">
        <h3>Timing</h3>
        <div class="two">
          <div class="field">
            <label for="start">Trip start</label>
            <input id="start" v-model="form.trip_start_date" type="date" />
          </div>
          <div class="field">
            <label for="end">Trip end</label>
            <input id="end" v-model="form.trip_end_date" type="date" />
          </div>
        </div>
        <div class="two">
          <div class="field">
            <label for="vd">Visa / permit deadline</label>
            <input id="vd" v-model="form.visa_deadline_date" type="date" />
          </div>
          <div class="field">
            <label for="vn">What expires</label>
            <input id="vn" v-model="form.visa_deadline_note" placeholder="Thai visa exemption" />
          </div>
        </div>
        <p class="muted small aside">
          A deadline is checked against every option you are given, and named in the
          answer. It is the one field that can rule a country out on its own.
        </p>
      </div>

      <div class="sub">
        <h3>What you are into</h3>
        <TagInput
          :model-value="interests"
          hint="Saves as you go"
          placeholder="trekking"
          :suggestions="INTEREST_SUGGESTIONS"
          @update:model-value="saveInterests"
        />
      </div>

      <div class="row actions">
        <button class="primary" :disabled="busy" type="submit">Save</button>
        <button class="danger" type="button" :disabled="busy" @click="forgetAll">
          Forget everything
        </button>
      </div>
    </form>

    <div class="lists">
      <!-- ================================================ 2. history -->
      <section class="panel">
        <div class="panel-head">
          <h2>Where you have been</h2>
          <p class="muted small">
            Your route, and what you made of it.
            <template v-if="history.length">
              {{ rated }} of {{ history.length }} rated.
            </template>
          </p>
        </div>

        <p class="muted small aside">
          Ratings do real work: somewhere similar to a place you rated 1–2 has to
          justify itself before it gets recommended to you.
        </p>

        <ul v-if="route.length" class="stops">
          <li v-for="stop in route" :key="stop.location">
            <div class="stop-head">
              <span class="place">{{ stop.location }}</span>
              <span v-if="stop.country" class="muted small">{{ stop.country }}</span>
              <span v-if="stop.source === 'tracked'" class="tag">auto-logged</span>
              <button
                class="ghost drop"
                type="button"
                :disabled="busy"
                :title="`Remove ${stop.location}`"
                @click="removeStop(stop.location)"
              >×</button>
            </div>
            <StarRating
              :model-value="stop.rating"
              :label="`How was ${stop.location}?`"
              @update:model-value="(r) => rateStop(stop, r)"
            />
            <p v-if="stop.review_notes" class="muted small note">“{{ stop.review_notes }}”</p>
          </li>
        </ul>
        <p v-else class="muted small">
          Nothing logged yet. Add a stop below, or just tell the chat where you have been.
        </p>

        <form class="add" @submit.prevent="addStop">
          <input v-model="newStop.location" placeholder="Add somewhere you have been" aria-label="Place" />
          <input v-model="newStop.country" class="narrow" placeholder="Country" aria-label="Country" />
          <button :disabled="busy || !newStop.location.trim()" type="submit">Add</button>
        </form>

        <details class="departures">
          <summary class="muted small">Left a country for good?</summary>
          <p class="muted small aside">
            This moves a whole country out of active context and into your
            country-level history — the “I am done with Thailand” case.
          </p>
          <form class="add" @submit.prevent="logDeparture">
            <input v-model="departure.country" placeholder="Laos" aria-label="Country left" />
            <input v-model="departure.departure_date" class="narrow" type="date" aria-label="Departure date" />
            <button :disabled="busy || !departure.country.trim()" type="submit">Log</button>
          </form>
          <ul v-if="visited.length" class="visited">
            <li v-for="(v, i) in visited" :key="i">
              <span class="place">{{ v.country }}</span>
              <span v-if="v.departure_date" class="muted small">left {{ v.departure_date }}</span>
            </li>
          </ul>
        </details>
      </section>

      <!-- ================================================ 3. wishlist -->
      <section class="panel">
        <div class="panel-head">
          <h2>Where you want to go</h2>
          <p class="muted small">Anything you are aiming for — including somewhere you would go back to.</p>
        </div>

        <ul v-if="wishlist.length" class="wishes">
          <li v-for="item in wishlist" :key="item.location">
            <div class="wish-head">
              <span class="place">{{ item.location }}</span>
              <span v-if="item.revisit" class="tag go" title="Somewhere you have already been">going back</span>
              <button
                class="ghost drop"
                type="button"
                :disabled="busy"
                :title="`Remove ${item.location}`"
                @click="dropWish(item.location)"
              >×</button>
            </div>
            <div class="priority">
              <button
                v-for="p in PRIORITIES"
                :key="p.value"
                type="button"
                class="pri"
                :class="{ on: item.priority === p.value }"
                :disabled="busy"
                @click="setPriority(item, p.value)"
              >{{ p.label }}</button>
            </div>
            <p v-if="item.note" class="muted small note">{{ item.note }}</p>
          </li>
        </ul>
        <p v-else class="muted small">
          Nothing on the wishlist. Anything here gets prioritised when you ask
          where to go next.
        </p>

        <form class="add" @submit.prevent="addWish">
          <input v-model="newWish.location" placeholder="Add somewhere you want to go" aria-label="Place" />
          <select v-model.number="newWish.priority" class="narrow" aria-label="How keen">
            <option v-for="p in PRIORITIES" :key="p.value" :value="p.value">{{ p.label }}</option>
          </select>
          <button :disabled="busy || !newWish.location.trim()" type="submit">Add</button>
        </form>
      </section>
    </div>

    <!-- ============================================== memory audit trail -->
    <section class="panel audit">
      <button class="ghost small toggle" type="button" @click="showWrites = !showWrites">
        {{ showWrites ? 'Hide' : 'Show' }} what has been written to memory
        ({{ writes.length }})
      </button>
      <template v-if="showWrites">
        <p class="muted small aside">
          Every write to your profile, whether the assistant inferred it or you
          typed it here.
        </p>
        <ul v-if="writes.length" class="writes">
          <li v-for="(w, i) in writes" :key="i">
            <div class="row">
              <span class="mono op">{{ w.operation }}</span>
              <span class="tag">{{ w.source }}</span>
              <span class="muted small">{{ w.created_at }}</span>
            </div>
            <div class="muted small">
              {{ Object.entries(w.payload).map(([k, v]) => `${k}=${v}`).join(', ') || '—' }}
            </div>
          </li>
        </ul>
        <p v-else class="muted small">No writes yet.</p>
      </template>
    </section>
  </div>
</template>

<style scoped>
.wrap { max-width: 1080px; margin: 0 auto; display: flex; flex-direction: column; gap: 18px; }

.top { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
h1 { margin: 0 0 4px; font-size: 22px; }
.intro { margin: 0; max-width: 620px; }
.redo { color: var(--muted); text-decoration: none; flex: none; }

.panel-head { margin-bottom: 16px; }
.panel-head h2 { margin: 0 0 3px; font-size: 16px; }
.panel-head p { margin: 0; }

h3 { margin: 0 0 12px; font-size: 13px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }

.two { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 700px) { .two { grid-template-columns: 1fr; } }

.aside { margin: 0 0 16px; max-width: 640px; }

.scales { display: grid; grid-template-columns: 1fr 1fr; gap: 0 26px; }
@media (max-width: 860px) { .scales { grid-template-columns: 1fr; } }

.sub { border-top: 1px solid var(--line); padding-top: 16px; margin-top: 4px; }
.actions { margin-top: 6px; }

/* ------------------------------------------------------------ the two lists */
.lists { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; align-items: start; }
@media (max-width: 860px) { .lists { grid-template-columns: 1fr; } }

ul { margin: 0; padding: 0; list-style: none; }

.stops li, .wishes li {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: var(--bg);
}
.stop-head, .wish-head { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
.place { font-size: 14px; text-transform: capitalize; }
.stop-head .muted, .wish-head .muted { text-transform: capitalize; }
.drop {
  margin-left: auto;
  border: none; background: none; color: var(--muted);
  padding: 0 4px; font-size: 17px; line-height: 1;
}
.drop:hover:not(:disabled) { color: var(--bad); }
.note { margin: 5px 0 0; font-style: italic; word-break: break-word; }

.priority { display: flex; gap: 5px; }
.pri {
  padding: 3px 10px;
  font-size: 11.5px;
  border-radius: 999px;
  background: transparent;
  color: var(--muted);
}
.pri.on { background: var(--accent-dim); border-color: var(--accent); color: #e9fff4; }

.add { display: flex; gap: 8px; margin-top: 12px; }
.add .narrow { max-width: 140px; }
.add button { flex: none; }

.departures { margin-top: 16px; border-top: 1px solid var(--line); padding-top: 12px; }
.departures summary { cursor: pointer; }
.departures .aside { margin-top: 10px; }
.visited { margin-top: 10px; }
.visited li { display: flex; gap: 8px; font-size: 13.5px; margin-bottom: 3px; }

/* ------------------------------------------------------------------- audit */
.audit { padding: 14px 18px; }
.toggle { padding: 0; border: none; color: var(--muted); }
.toggle:hover { color: var(--text); }
.audit .aside { margin-top: 12px; }
.writes li { margin-bottom: 11px; }
.op { font-size: 12px; color: var(--accent); }
</style>
