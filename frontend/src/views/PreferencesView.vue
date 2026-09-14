<script setup>
// The trip profile, as three sections rather than one very long scroll.
//
// The three sections map onto three genuinely different questions:
//
//   Profile   - who you are and how you travel. A form: edit, then save.
//   Route     - where you have been, and what you thought of it. The ratings
//               here are read before every recommendation, which is why they
//               are one tap and always editable.
//   Wishlist  - where you want to go. Somewhere you have already been is
//               allowed: wanting a second go at a place is a real preference.
//
// They used to be stacked panels on one page, which on a phone meant scrolling
// past the whole profile form and the entire route to reach the wishlist. Now
// they are tabs, so each one is one tap and starts at the top.
//
// Route and wishlist actions persist immediately, because each one is a
// discrete action rather than an edit-in-progress. Only the profile form has a
// Save button, because that is the only section where you are mid-thought - and
// it now announces itself in a sticky bar the moment something is unsaved,
// rather than waiting at the bottom of a form you have to scroll back down.
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, session, tokens } from '../api'
import {
  BUDGET_BANDS,
  CLIMATE_PREFS,
  PRIORITIES,
  SOCIAL_STYLES,
  TRAVEL_STYLES
} from '../preferences'
import ScalePicker from '../components/ScalePicker.vue'
import SegmentedTabs from '../components/SegmentedTabs.vue'
import StarRating from '../components/StarRating.vue'
import TagInput from '../components/TagInput.vue'

const router = useRouter()

const INTEREST_SUGGESTIONS = [
  'nature', 'food', 'trekking', 'diving', 'beaches', 'history',
  'nightlife', 'culture', 'markets', 'wildlife', 'surfing', 'photography'
]

const EMPTY = {
  passports: [],
  current_location: '',
  budget_band: '',
  travel_style: '',
  climate_preference: '',
  social_style: '',
  visa_deadline_date: '',
  visa_deadline_note: ''
}

const form = ref({ ...EMPTY })
// What the form looked like when it was last loaded or saved, so the save bar
// can appear only when there is genuinely something to save.
const clean = ref(JSON.stringify(EMPTY))

const history = ref([])
const wishlist = ref([])
const interests = ref([])
const visited = ref([])

const newStop = ref({ location: '', country: '' })
const newWish = ref({ location: '', priority: 2 })
const departure = ref({ country: '', departure_date: '' })

const tab = ref('profile')
const busy = ref(false)
const error = ref('')
const saved = ref('')

// Newest first: the stop you just left is the one you are most likely to rate.
const route = computed(() => [...history.value].slice().reverse())
const rated = computed(() => history.value.filter((h) => h.rating).length)
const dirty = computed(() => JSON.stringify(form.value) !== clean.value)

// A country-level stop stores the same string as both location and country, so
// printing both just repeats the place name back at you.
const showCountry = (stop) =>
  stop.country && stop.country.toLowerCase() !== stop.location.toLowerCase()

const TABS = computed(() => [
  { id: 'profile', label: 'Profile' },
  { id: 'route', label: 'Route', count: history.value.length },
  { id: 'wishlist', label: 'Wishlist', count: wishlist.value.length }
])

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
  for (const key of Object.keys(EMPTY)) {
    form.value[key] = key === 'passports' ? [...(profile.passports || [])] : profile[key] ?? ''
  }
  clean.value = JSON.stringify(form.value)
  visited.value = res.visited_history || []
}

function applyTravel(res) {
  if (res.travel_history) history.value = res.travel_history
  if (res.wishlist) wishlist.value = res.wishlist
  if (res.interests) interests.value = res.interests
}

/** Run one mutating call, keeping the sections in sync and surfacing failures. */
async function act(fn, message = '') {
  error.value = ''
  saved.value = ''
  busy.value = true
  try {
    applyTravel(await fn())
    saved.value = message
    // The mirrored interests text and the departure log live on the profile
    // side, so a travel write has to refresh both or the two drift apart.
    applyProfile(await api.getProfile())
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

// ------------------------------------------------------------------ profile
async function saveProfile() {
  error.value = ''
  saved.value = ''
  busy.value = true
  try {
    // This form renders every field it can write, so an empty control genuinely
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

function revert() {
  form.value = JSON.parse(clean.value)
}

async function saveInterests(next) {
  interests.value = next
  await act(() => api.setInterests(next), 'Interests updated.')
}

// -------------------------------------------------------------------- route
function addStop() {
  const location = newStop.value.location.trim()
  if (!location) return
  const country = newStop.value.country.trim()
  newStop.value = { location: '', country: '' }
  return act(
    () => api.addVisit({ location, country: country || null }),
    `${location} added to your route.`
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
    // A full forget resets onboarding too, so the router's onboarding gate must
    // stop trusting its cached "already onboarded" answer.
    session.reset()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

// This used to be a plain link straight to /welcome, which did nothing useful:
// the welcome page computes its first question from the SAME answered list
// that was already complete, so it landed straight back on the review screen
// with nothing to redo. It has to actually reset progress first.
async function redoOnboarding() {
  busy.value = true
  error.value = ''
  try {
    await api.resetOnboardingDebug()
    session.reset()
    router.push('/welcome')
  } catch (e) {
    error.value = e.message
    busy.value = false
  }
}
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1 class="grad-text">Your trip</h1>
        <p class="muted small">
          Every agent reads this before it answers, so you never have to repeat
          yourself. Change anything here and the next recommendation reflects it.
        </p>
      </div>
    </header>

    <SegmentedTabs v-model="tab" :tabs="TABS" label="Trip sections" />

    <Transition name="fade-slide" mode="out-in">
      <div v-if="error" key="err" class="error">{{ error }}</div>
      <div v-else-if="saved" key="ok" class="notice">{{ saved }}</div>
    </Transition>

    <!-- ==================================================== 1. profile -->
    <form v-show="tab === 'profile'" class="panel section" @submit.prevent="saveProfile">
      <div class="panel-head">
        <h2>About you</h2>
        <p class="muted small">Who you are and how you travel.</p>
      </div>

      <div class="two">
        <TagInput
          v-model="form.passports"
          label="Nationality / passports"
          hint="First one is primary"
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
        <ScalePicker v-model="form.budget_band" label="Budget band" :options="BUDGET_BANDS" />
        <ScalePicker v-model="form.travel_style" label="Travel pace" :options="TRAVEL_STYLES" />
        <ScalePicker v-model="form.climate_preference" label="Climate preference" :options="CLIMATE_PREFS" />
        <ScalePicker v-model="form.social_style" label="Travelling" :options="SOCIAL_STYLES" />
      </div>

      <div class="sub">
        <p class="eyebrow">Deadline</p>
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
        <p class="eyebrow">What you are into</p>
        <TagInput
          :model-value="interests"
          hint="Saves as you go"
          placeholder="trekking"
          :suggestions="INTEREST_SUGGESTIONS"
          @update:model-value="saveInterests"
        />
      </div>

      <div class="sub danger-zone">
        <p class="eyebrow">Start over</p>
        <div class="cluster">
          <button class="small" type="button" :disabled="busy" @click="redoOnboarding">
            Redo the questions
          </button>
          <button class="danger small" type="button" :disabled="busy" @click="forgetAll">
            Forget everything
          </button>
        </div>
      </div>

      <!-- Sticky, and only while there is something to save. On a phone this is
           what stops a long form ending in a button you have to hunt for. -->
      <Transition name="fade-slide">
        <div v-if="dirty" class="savebar">
          <span class="muted small grow">Unsaved changes</span>
          <button class="ghost small" type="button" :disabled="busy" @click="revert">Discard</button>
          <button class="primary small" :disabled="busy" type="submit">Save</button>
        </div>
      </Transition>
    </form>

    <!-- ====================================================== 2. route -->
    <section v-show="tab === 'route'" class="panel section">
      <div class="panel-head">
        <h2>Where you have been</h2>
        <p class="muted small">
          Your route, and what you made of it.
          <template v-if="history.length">{{ rated }} of {{ history.length }} rated.</template>
        </p>
      </div>

      <p class="muted small aside">
        Ratings do real work: somewhere similar to a place you rated 1–2 has to
        justify itself before it gets recommended to you.
      </p>

      <form class="add" @submit.prevent="addStop">
        <input v-model="newStop.location" placeholder="Add somewhere you have been" aria-label="Place" />
        <input v-model="newStop.country" placeholder="Country" aria-label="Country" />
        <button :disabled="busy || !newStop.location.trim()" type="submit">Add</button>
      </form>

      <TransitionGroup v-if="route.length" tag="ul" name="fade-slide" class="rows">
        <li v-for="stop in route" :key="stop.location">
          <div class="row-head">
            <span class="place grow">{{ stop.location }}</span>
            <span v-if="stop.source === 'tracked'" class="tag">auto</span>
            <button
              class="icon-btn destructive"
              type="button"
              :disabled="busy"
              :title="`Remove ${stop.location}`"
              :aria-label="`Remove ${stop.location}`"
              @click="removeStop(stop.location)"
            >×</button>
          </div>
          <p v-if="showCountry(stop)" class="muted small country">{{ stop.country }}</p>
          <StarRating
            :model-value="stop.rating"
            :label="`How was ${stop.location}?`"
            @update:model-value="(r) => rateStop(stop, r)"
          />
          <p v-if="stop.review_notes" class="muted small note">“{{ stop.review_notes }}”</p>
        </li>
      </TransitionGroup>
      <div v-else class="empty-state">
        <span class="glyph" aria-hidden="true">🧭</span>
        <p>Nothing logged yet. Add a stop above, or just tell the chat where you have been.</p>
      </div>

      <details class="departures">
        <summary class="muted small">Left a country for good?</summary>
        <p class="muted small aside">
          This moves a whole country out of active context and into your
          country-level history — the “I am done with Thailand” case.
        </p>
        <form class="add" @submit.prevent="logDeparture">
          <input v-model="departure.country" placeholder="Laos" aria-label="Country left" />
          <input v-model="departure.departure_date" type="date" aria-label="Departure date" />
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

    <!-- =================================================== 3. wishlist -->
    <section v-show="tab === 'wishlist'" class="panel section">
      <div class="panel-head">
        <h2>Where you want to go</h2>
        <p class="muted small">Anything you are aiming for — including somewhere you would go back to.</p>
      </div>

      <form class="add" @submit.prevent="addWish">
        <input v-model="newWish.location" placeholder="Add somewhere you want to go" aria-label="Place" />
        <select v-model.number="newWish.priority" aria-label="How keen">
          <option v-for="p in PRIORITIES" :key="p.value" :value="p.value">{{ p.label }}</option>
        </select>
        <button :disabled="busy || !newWish.location.trim()" type="submit">Add</button>
      </form>

      <TransitionGroup v-if="wishlist.length" tag="ul" name="fade-slide" class="rows">
        <li v-for="item in wishlist" :key="item.location">
          <div class="row-head">
            <span class="place grow">{{ item.location }}</span>
            <span v-if="item.revisit" class="tag go" title="Somewhere you have already been">going back</span>
            <button
              class="icon-btn destructive"
              type="button"
              :disabled="busy"
              :title="`Remove ${item.location}`"
              :aria-label="`Remove ${item.location}`"
              @click="dropWish(item.location)"
            >×</button>
          </div>
          <div class="priority" role="group" :aria-label="`How keen on ${item.location}`">
            <button
              v-for="p in PRIORITIES"
              :key="p.value"
              type="button"
              class="pri"
              :class="{ on: item.priority === p.value }"
              :aria-pressed="item.priority === p.value"
              :disabled="busy"
              @click="setPriority(item, p.value)"
            >{{ p.label }}</button>
          </div>
          <p v-if="item.note" class="muted small note">{{ item.note }}</p>
        </li>
      </TransitionGroup>
      <div v-else class="empty-state">
        <span class="glyph" aria-hidden="true">✦</span>
        <p>Nothing on the wishlist. Anything here gets prioritised when you ask where to go next.</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.section { animation: fadeIn var(--dur) var(--ease-out) both; }

.panel-head h2 { font-size: var(--fs-h2); }

.two { display: grid; grid-template-columns: 1fr 1fr; gap: 0 var(--sp-4); }
@media (max-width: 700px) { .two { grid-template-columns: 1fr; } }

.aside { margin: 0 0 var(--sp-4); max-width: 64ch; }

.scales { display: grid; grid-template-columns: 1fr 1fr; gap: 0 var(--sp-7); }
@media (max-width: 860px) { .scales { grid-template-columns: 1fr; } }

.sub { border-top: 1px solid var(--line); padding-top: var(--sp-4); margin-top: var(--sp-2); }
.danger-zone { margin-top: var(--sp-5); }

/* ---------------------------------------------------------------- save bar */
.savebar {
  position: sticky;
  /* Above the mobile tab bar; --tabbar-h is 0 on desktop. */
  bottom: calc(var(--tabbar-h) + var(--safe-b) + var(--sp-2));
  z-index: 15;
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: var(--sp-5) 0 0;
  padding: var(--sp-3);
  border: 1px solid var(--accent-dim);
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--panel-2) 94%, transparent);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: var(--shadow-md);
}

/* -------------------------------------------------------------- add a row
   Three controls that must never be squeezed into one unusable line on a
   phone: below 620px the name takes the full width and the qualifier sits
   next to the button on a second row. */
.add {
  display: grid;
  grid-template-columns: 1fr 150px auto;
  gap: var(--sp-2);
  margin-bottom: var(--sp-4);
}
.add button { flex: none; }
@media (max-width: 620px) {
  .add { grid-template-columns: 1fr auto; }
  .add > :first-child { grid-column: 1 / -1; }
}

/* ------------------------------------------------------------------- rows */
.rows { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: var(--sp-2); }
.rows li {
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: var(--sp-3);
  background: var(--bg);
  transition: border-color var(--dur) ease;
}
.rows li:hover { border-color: var(--stone-600); }

.row-head { display: flex; align-items: center; gap: var(--sp-2); }
.place { font-size: 14.5px; font-weight: 550; text-transform: capitalize; min-width: 0; overflow-wrap: anywhere; }
.country { margin: 0 0 var(--sp-2); text-transform: capitalize; }
.note { margin: var(--sp-2) 0 0; font-style: italic; word-break: break-word; }

.priority { display: flex; flex-wrap: wrap; gap: 5px; margin-top: var(--sp-1); }
.pri {
  padding: 5px 12px;
  font-size: 12px;
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--muted);
}
.pri.on { background: var(--accent-dim); border-color: var(--accent); color: var(--text); font-weight: 600; }

/* ------------------------------------------------------------- departures */
.departures { margin-top: var(--sp-5); border-top: 1px solid var(--line); padding-top: var(--sp-4); }
.departures summary { cursor: pointer; padding: var(--sp-1) 0; }
.departures .aside { margin-top: var(--sp-3); }
.visited { margin: var(--sp-3) 0 0; padding: 0; list-style: none; }
.visited li { display: flex; flex-wrap: wrap; gap: var(--sp-2); font-size: 13.5px; margin-bottom: 3px; }
.visited .place { text-transform: capitalize; font-weight: 400; font-size: 13.5px; }
</style>
