<script setup>
// The welcome page. This is the first thing a new account sees, and it replaces
// the old first-run experience, which was the ordinary chat screen with an agent
// asking the questions one turn at a time.
//
// Three things are different, and each one fixes something that was wrong:
//
//  1. The questions come from the backend as fixed data, not from a model. They
//     are the same every time, so nobody is asked the same thing twice and the
//     eval suite has something stable to assert against.
//  2. Every answer is echoed back as "here is what I took from that" the instant
//     it is extracted. Extraction is not perfect; showing its working straight
//     away is what makes that acceptable rather than alarming.
//  3. It ends on a review screen where every captured field is editable by hand.
//     Nothing here is a one-way door.
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, tokens } from '../api'
import { labelFor, priorityLabel } from '../preferences'
import StarRating from '../components/StarRating.vue'

const router = useRouter()
const route = useRoute()

const questions = ref([])
const stepId = ref(null)
const answer = ref('')
const busy = ref(false)
const loading = ref(true)
const error = ref('')
const note = ref('')
const justCaptured = ref([])
const answered = ref([])
const box = ref(null)

const profile = ref({})
const history = ref([])
const wishlist = ref([])
const interests = ref([])

const question = computed(() => questions.value.find((q) => q.id === stepId.value) || null)
const position = computed(() => questions.value.findIndex((q) => q.id === stepId.value) + 1)
const progress = computed(() =>
  questions.value.length ? Math.round((answered.value.length / questions.value.length) * 100) : 0
)

// Something worth showing on the right-hand panel: until the first answer lands
// there is nothing to display, and an empty panel reads as a broken one.
const hasCapture = computed(
  () => history.value.length || wishlist.value.length || interests.value.length ||
    (profile.value.passports || []).length || profile.value.budget_band ||
    profile.value.travel_style || profile.value.climate_preference
)

onMounted(load)

async function load() {
  try {
    const res = await api.startOnboarding()
    questions.value = res.questions || []
    answered.value = res.state?.answered || []
    stepId.value = res.next_step || null
    apply(res)
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      tokens.clearUser()
      router.push('/login')
      return
    }
    error.value = e.message
  } finally {
    loading.value = false
    focusBox()
  }
}

function apply(res) {
  if (res.profile) profile.value = res.profile
  if (res.travel_history) history.value = res.travel_history
  if (res.wishlist) wishlist.value = res.wishlist
  if (res.interests) interests.value = res.interests
}

async function focusBox() {
  await nextTick()
  box.value?.focus()
}

watch(stepId, () => {
  answer.value = ''
  focusBox()
})

async function submit(skipped = false) {
  if (busy.value || !stepId.value) return
  if (!skipped && !answer.value.trim()) return

  busy.value = true
  error.value = ''
  note.value = ''
  justCaptured.value = []
  const current = stepId.value

  try {
    const res = await api.answerOnboarding(current, answer.value, skipped)
    apply(res)
    answered.value = res.state?.answered || [...answered.value, current]
    justCaptured.value = skipped ? [] : res.captured || []
    note.value = res.note || ''
    if (res.next_step) {
      stepId.value = res.next_step
    } else {
      stepId.value = null
    }
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

// Ctrl/Cmd+Enter sends. A plain Enter has to stay a newline: the whole premise
// is a paragraph of plain text, and hijacking Enter would fight that.
function onKeydown(event) {
  if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
    event.preventDefault()
    submit()
  }
}

function jumpTo(id) {
  if (busy.value) return
  stepId.value = id
}

async function finish() {
  busy.value = true
  try {
    await api.completeOnboarding()
    router.push(route.query.next || '/chat')
  } catch (e) {
    error.value = e.message
    busy.value = false
  }
}

async function skipAll() {
  busy.value = true
  try {
    await api.skipOnboarding()
    router.push(route.query.next || '/chat')
  } catch (e) {
    error.value = e.message
    busy.value = false
  }
}

function describe(write) {
  const p = write.payload || {}
  switch (write.operation) {
    case 'add_travel_history':
      return p.rating ? `${p.location} — rated ${p.rating}/5` : `${p.location}`
    case 'add_wishlist':
      return `${p.location}${p.revisit ? ' (going back)' : ''} — ${priorityLabel(p.priority)}`
    case 'set_passports':
      return (p.passports || []).join(' and ')
    case 'set_interests':
      return (p.interests || []).join(', ')
    case 'set_social_style':
      return labelFor(p.social_style)
    case 'update_profile':
      return Object.entries(p)
        .map(([key, value]) => `${FIELD_LABELS[key] || key}: ${labelFor(value) || value}`)
        .join(' · ')
    default:
      return JSON.stringify(p)
  }
}

const WRITE_LABELS = {
  add_travel_history: 'Been there',
  add_wishlist: 'Want to go',
  set_passports: 'Passport',
  set_interests: 'Into',
  set_social_style: 'Travelling',
  update_profile: 'Noted'
}

const FIELD_LABELS = {
  budget_band: 'Budget',
  travel_style: 'Pace',
  climate_preference: 'Climate',
  current_location: 'Currently in',
  visa_deadline_date: 'Deadline',
  visa_deadline_note: 'What expires'
}
</script>

<template>
  <div class="welcome">
    <div v-if="loading" class="panel loading muted">Getting things ready…</div>

    <template v-else>
      <header class="intro">
        <h1>Welcome to Travel Steezy</h1>
        <p class="muted">
          Five questions, answered however you like — full sentences, a scribbled list,
          whatever comes out. I will turn it into a profile you can edit, and then I
          never have to ask you any of it again.
        </p>
      </header>

      <div class="rail">
        <div class="bar"><div class="fill" :style="{ width: `${progress}%` }" /></div>
        <ol class="steps">
          <li
            v-for="(q, index) in questions"
            :key="q.id"
            :class="{
              done: answered.includes(q.id),
              current: q.id === stepId,
              clickable: answered.includes(q.id) || q.id === stepId
            }"
            @click="answered.includes(q.id) && jumpTo(q.id)"
          >
            <span class="pip">{{ answered.includes(q.id) ? '✓' : index + 1 }}</span>
            <span class="name">{{ q.title }}</span>
          </li>
        </ol>
      </div>

      <div class="cols">
        <Transition name="fade-slide" mode="out-in">
        <!-- ---------------------------------------------- the question -->
        <section v-if="question" :key="stepId" class="panel ask">
          <p class="step muted small">Question {{ position }} of {{ questions.length }}</p>
          <h2>{{ question.title }}</h2>
          <p class="prompt">{{ question.prompt }}</p>
          <p class="muted small hint">{{ question.hint }}</p>

          <textarea
            ref="box"
            v-model="answer"
            rows="6"
            :placeholder="question.placeholder"
            :disabled="busy"
            :aria-label="question.title"
            @keydown="onKeydown"
          />

          <div class="actions">
            <button class="primary" :disabled="busy || !answer.trim()" @click="submit()">
              {{ busy ? 'Reading that…' : 'Next' }}
            </button>
            <button class="ghost small" :disabled="busy" @click="submit(true)">
              {{ question.optional ? 'Skip — not relevant' : "Skip, I'll add it later" }}
            </button>
            <span class="muted small shortcut hide-narrow">Ctrl + Enter</span>
          </div>

          <p v-if="note" class="notice soft">{{ note }}</p>
          <div v-if="error" class="error">{{ error }}</div>

          <button class="ghost small bail" :disabled="busy" @click="skipAll">
            Skip all of this and go straight to the chat
          </button>
        </section>

        <!-- ---------------------------------------------- the review step -->
        <section v-else key="done" class="panel ask done-panel">
          <h2>That is your profile built</h2>
          <p class="muted">
            Everything below is stored against your account and read before every
            answer you get. Check it over — anything that came out wrong is fixable
            now, and any time after, in My Preferences.
          </p>
          <div v-if="error" class="error">{{ error }}</div>
          <div class="actions">
            <button class="primary" :disabled="busy" @click="finish">Start exploring</button>
            <RouterLink class="ghost small link" to="/preferences">Edit it in full first</RouterLink>
          </div>
          <p class="muted small revisit">
            Want to redo an answer? Click any completed step above.
          </p>
        </section>
        </Transition>

        <!-- ---------------------------------------------- what was captured -->
        <aside class="panel captured">
          <h3>What I have so far</h3>

          <Transition name="pop">
          <div v-if="justCaptured.length" class="just">
            <h4>From that answer</h4>
            <ul>
              <li v-for="(w, i) in justCaptured" :key="i">
                <span class="op">{{ WRITE_LABELS[w.operation] || w.operation }}</span>
                <span class="what">{{ describe(w) }}</span>
              </li>
            </ul>
          </div>
          </Transition>

          <p v-if="!hasCapture" class="muted small empty">
            Nothing yet. Answer the first question and it will start filling in here.
          </p>

          <template v-else>
            <div v-if="history.length" class="group">
              <h4>Been to</h4>
              <ul class="places">
                <li v-for="stop in history" :key="stop.location">
                  <span class="place">{{ stop.location }}</span>
                  <StarRating v-if="stop.rating" :model-value="stop.rating" readonly />
                </li>
              </ul>
            </div>

            <div v-if="wishlist.length" class="group">
              <h4>Want to go</h4>
              <ul class="places">
                <li v-for="item in wishlist" :key="item.location">
                  <span class="place">{{ item.location }}</span>
                  <span class="tag" :class="{ go: item.priority === 1 }">
                    {{ item.revisit ? 'again' : priorityLabel(item.priority) }}
                  </span>
                </li>
              </ul>
            </div>

            <div v-if="(profile.passports || []).length" class="group">
              <h4>Passport{{ profile.passports.length > 1 ? 's' : '' }}</h4>
              <div class="chips">
                <span v-for="p in profile.passports" :key="p" class="tag">{{ p }}</span>
              </div>
            </div>

            <div v-if="profile.budget_band || profile.travel_style || profile.climate_preference || profile.social_style" class="group">
              <h4>How you travel</h4>
              <dl>
                <template v-if="profile.budget_band"><dt>Budget</dt><dd>{{ labelFor(profile.budget_band) }}</dd></template>
                <template v-if="profile.travel_style"><dt>Pace</dt><dd>{{ labelFor(profile.travel_style) }}</dd></template>
                <template v-if="profile.climate_preference"><dt>Climate</dt><dd>{{ labelFor(profile.climate_preference) }}</dd></template>
                <template v-if="profile.social_style"><dt>Company</dt><dd>{{ labelFor(profile.social_style) }}</dd></template>
                <template v-if="profile.current_location"><dt>Currently in</dt><dd>{{ profile.current_location }}</dd></template>
                <template v-if="profile.visa_deadline_date"><dt>Deadline</dt><dd class="deadline">{{ profile.visa_deadline_date }}</dd></template>
              </dl>
            </div>

            <div v-if="interests.length" class="group">
              <h4>Into</h4>
              <div class="chips">
                <span v-for="i in interests" :key="i" class="tag">{{ i }}</span>
              </div>
            </div>
          </template>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.welcome { max-width: var(--container); margin: 0 auto; }
.loading { text-align: center; padding: 60px 20px; }

.intro { text-align: center; margin-bottom: 22px; animation: fadeInUp var(--dur-slow) var(--ease-out) both; }
.intro h1 {
  margin: 0 0 6px;
  font-size: 25px;
  background: linear-gradient(90deg, var(--text), var(--accent-bright));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}
.intro p { margin: 0 auto; max-width: 560px; font-size: 14px; }

/* ---------------------------------------------------------------- progress */
.rail { margin-bottom: 18px; }
.bar { height: 4px; background: var(--line); border-radius: 999px; overflow: hidden; }
.fill {
  height: 100%;
  background: var(--accent-grad);
  background-size: 200% 100%;
  border-radius: 999px;
  transition: width var(--dur-slow) var(--ease-out);
  animation: shimmer 2.5s linear infinite;
}

.steps {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
}
.steps li { display: flex; align-items: center; gap: 7px; font-size: 12.5px; color: var(--muted); min-width: 0; transition: color var(--dur) ease; }
.steps li.clickable { cursor: pointer; }
.steps li.done .pip { background: var(--accent); border-color: var(--accent); color: var(--on-accent); animation: popIn var(--dur) var(--ease-spring) both; }
.steps li.current { color: var(--text); }
.steps li.current .pip { border-color: var(--accent); color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.steps li.done:hover .name { color: var(--text); }
.steps li.done:hover .pip, .steps li.current:hover .pip { transform: scale(1.1); }
.pip {
  display: grid;
  place-items: center;
  flex: none;
  width: 20px; height: 20px;
  border: 1px solid var(--line);
  border-radius: 50%;
  font-size: 11px;
  transition: transform var(--dur-fast) var(--ease-spring), box-shadow var(--dur) ease;
}
.name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 760px) { .steps .name { display: none; } .steps { justify-content: center; gap: 10px; } }

/* ------------------------------------------------------------------ layout */
.cols {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}
@media (max-width: 860px) { .cols { grid-template-columns: 1fr; } }

/* ---------------------------------------------------------------- question */
.step { margin: 0 0 4px; letter-spacing: .04em; text-transform: uppercase; font-size: 11px; }
.ask h2 { margin: 0 0 6px; font-size: 20px; }
.prompt { margin: 0 0 4px; font-size: 14.5px; }
.hint { margin: 0 0 14px; }

textarea {
  resize: vertical;
  min-height: 120px;
  line-height: 1.55;
}
textarea::placeholder { color: var(--muted-2); }

.actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 14px; }
.shortcut { margin-left: auto; }
.link { color: var(--accent); text-decoration: none; font-size: 13px; }

.soft { margin: 14px 0 0; }
.bail {
  display: block;
  margin: 18px auto 0;
  color: var(--muted);
  border: none;
  font-size: 12.5px;
}
.bail:hover { color: var(--text); }

.done-panel h2 { margin-bottom: 8px; }
.done-panel p { font-size: 14px; }
.revisit { margin: 14px 0 0; }

/* ---------------------------------------------------------------- captured */
.captured { position: sticky; top: 20px; }
.captured h3 { margin: 0 0 12px; font-size: 15px; }
h4 {
  margin: 0 0 7px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--muted);
}

.just {
  background: var(--moss-soft);
  border: 1px solid var(--moss-dim);
  border-radius: var(--radius-sm);
  padding: 11px 12px;
  margin-bottom: 16px;
  box-shadow: var(--glow-moss);
}
.just ul { margin: 0; padding: 0; list-style: none; }
.just li { display: flex; gap: 8px; font-size: 13px; margin-bottom: 4px; }
.just li:last-child { margin-bottom: 0; }
.op { flex: none; color: var(--moss-bright); font-size: 11px; text-transform: uppercase; letter-spacing: .04em; padding-top: 2px; }
.what { color: var(--text); word-break: break-word; }

.group { margin-bottom: 16px; }
.group:last-child { margin-bottom: 0; }

.places { list-style: none; margin: 0; padding: 0; }
.places li { display: flex; align-items: center; gap: 8px; font-size: 13.5px; margin-bottom: 5px; }
.place { text-transform: capitalize; }

.chips { display: flex; flex-wrap: wrap; gap: 5px; }

dl { display: grid; grid-template-columns: 88px 1fr; gap: 4px 10px; margin: 0; font-size: 13.5px; }
dt { color: var(--muted); }
dd { margin: 0; word-break: break-word; }
dd.deadline { color: var(--warn); }

.empty { margin: 0; }
</style>
