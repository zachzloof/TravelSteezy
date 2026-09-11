<script setup>
// Direct, non-conversational control over the memory store. Backed by
// GET /profile/me and PATCH /profile/me - the same rows the agents read, so an
// edit here visibly changes the next recommendation.
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api, tokens } from '../api'

const router = useRouter()

const form = ref({
  nationality: '',
  budget_band: '',
  travel_style: '',
  climate_preference: '',
  current_location: '',
  trip_start_date: '',
  trip_end_date: '',
  visa_deadline_date: '',
  visa_deadline_note: '',
  interests: ''
})
const visited = ref([])
const writes = ref([])
const departure = ref({ country: '', departure_date: '' })
const busy = ref(false)
const error = ref('')
const saved = ref('')

onMounted(load)

async function load() {
  try {
    const res = await api.getProfile()
    apply(res)
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      tokens.clearUser()
      router.push('/login')
    } else {
      error.value = e.message
    }
  }
}

function apply(res) {
  for (const key of Object.keys(form.value)) {
    form.value[key] = res.profile?.[key] ?? ''
  }
  visited.value = res.visited_history || []
  writes.value = res.recent_writes || []
}

async function save() {
  error.value = ''
  saved.value = ''
  busy.value = true
  try {
    // Send only non-empty values: PATCH must not blank fields the user left alone.
    const patch = {}
    for (const [key, value] of Object.entries(form.value)) {
      if (value !== '' && value !== null) patch[key] = value
    }
    apply(await api.patchProfile(patch))
    saved.value = 'Saved. The assistant will use this on your next message.'
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function logDeparture() {
  if (!departure.value.country.trim()) return
  error.value = ''
  busy.value = true
  try {
    apply(await api.logDeparture({
      country: departure.value.country.trim(),
      departure_date: departure.value.departure_date || null
    }))
    departure.value = { country: '', departure_date: '' }
    saved.value = 'Logged. That country moved from active context into your history.'
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function forgetAll() {
  if (!confirm('Erase everything Travel Steezy remembers about your trip? Your account stays.')) return
  busy.value = true
  try {
    apply(await api.forgetMe())
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
    <h1>My Preferences</h1>
    <p class="muted small intro">
      This is the trip profile Travel Steezy keeps for your account. Every agent reads it
      before answering, so you never have to repeat yourself. Change anything here
      and the next recommendation will reflect it.
    </p>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="saved" class="notice">{{ saved }}</div>

    <div class="cols">
      <form class="panel" @submit.prevent="save">
        <h3>Trip profile</h3>

        <div class="field">
          <label for="nat">Passport / nationality</label>
          <input id="nat" v-model="form.nationality" placeholder="United Kingdom" />
        </div>

        <div class="field">
          <label for="loc">Currently in</label>
          <input id="loc" v-model="form.current_location" placeholder="Thailand" />
        </div>

        <div class="pair">
          <div class="field">
            <label for="budget">Budget band</label>
            <select id="budget" v-model="form.budget_band">
              <option value="">not set</option>
              <option value="shoestring">Shoestring</option>
              <option value="mid">Mid-range</option>
              <option value="comfortable">Comfortable</option>
            </select>
          </div>
          <div class="field">
            <label for="pace">Travel pace</label>
            <select id="pace" v-model="form.travel_style">
              <option value="">not set</option>
              <option value="slow">Slow</option>
              <option value="balanced">Balanced</option>
              <option value="fast">Fast</option>
            </select>
          </div>
        </div>

        <div class="field">
          <label for="climate">Climate preference</label>
          <select id="climate" v-model="form.climate_preference">
            <option value="">not set</option>
            <option value="cool">Cool</option>
            <option value="temperate">Temperate</option>
            <option value="hot">Hot</option>
            <option value="no_preference">No preference</option>
          </select>
        </div>

        <div class="pair">
          <div class="field">
            <label for="start">Trip start</label>
            <input id="start" v-model="form.trip_start_date" type="date" />
          </div>
          <div class="field">
            <label for="end">Trip end</label>
            <input id="end" v-model="form.trip_end_date" type="date" />
          </div>
        </div>

        <div class="pair">
          <div class="field">
            <label for="vd">Visa / permit deadline</label>
            <input id="vd" v-model="form.visa_deadline_date" type="date" />
          </div>
          <div class="field">
            <label for="vn">What expires</label>
            <input id="vn" v-model="form.visa_deadline_note" placeholder="Thai visa exemption" />
          </div>
        </div>

        <div class="field">
          <label for="int">Interests</label>
          <textarea id="int" v-model="form.interests" rows="2" placeholder="diving, hiking, street food" />
        </div>

        <div class="row">
          <button class="primary" :disabled="busy" type="submit">Save preferences</button>
          <button class="danger" type="button" :disabled="busy" @click="forgetAll">Forget everything</button>
        </div>
      </form>

      <div class="side">
        <div class="panel">
          <h3>Visited history</h3>
          <p class="muted small">
            Append-only. A country moves here once you have left it, and drops out of
            active context.
          </p>
          <ul v-if="visited.length" class="visited">
            <li v-for="(v, i) in visited" :key="i">
              <span class="country">{{ v.country }}</span>
              <span v-if="v.departure_date" class="muted small"> left {{ v.departure_date }}</span>
            </li>
          </ul>
          <p v-else class="muted small">Nothing logged yet.</p>

          <form class="departure" @submit.prevent="logDeparture">
            <div class="field">
              <label for="dc">I have left…</label>
              <input id="dc" v-model="departure.country" placeholder="Laos" />
            </div>
            <div class="field">
              <label for="dd">Departure date</label>
              <input id="dd" v-model="departure.departure_date" type="date" />
            </div>
            <button :disabled="busy || !departure.country.trim()" type="submit">Log departure</button>
          </form>
        </div>

        <div class="panel">
          <h3>Recent memory writes</h3>
          <p class="muted small">Every write to your profile, agent-inferred or your own edit.</p>
          <ul v-if="writes.length" class="writes">
            <li v-for="(w, i) in writes" :key="i">
              <div class="row">
                <span class="mono op">{{ w.operation }}</span>
                <span class="tag">{{ w.source }}</span>
              </div>
              <div class="muted small">
                {{ Object.entries(w.payload).map(([k, v]) => `${k}=${v}`).join(', ') || '—' }}
              </div>
              <div class="muted small">{{ w.created_at }}</div>
            </li>
          </ul>
          <p v-else class="muted small">No writes yet.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wrap { max-width: 1050px; margin: 0 auto; }
h1 { margin: 0 0 4px; font-size: 22px; }
.intro { margin: 0 0 18px; max-width: 620px; }
h3 { margin: 0 0 12px; font-size: 15px; }

.cols { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr); gap: 18px; align-items: start; }
@media (max-width: 880px) { .cols { grid-template-columns: 1fr; } }

.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.side { display: flex; flex-direction: column; gap: 18px; }

ul { margin: 0; padding: 0; list-style: none; }
.visited li { font-size: 14px; margin-bottom: 4px; }
.country { text-transform: capitalize; }

.departure { margin-top: 16px; border-top: 1px solid var(--line); padding-top: 14px; }

.writes li { margin-bottom: 12px; }
.op { font-size: 12px; color: var(--accent); }
</style>
