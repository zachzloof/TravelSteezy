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
//
// On a phone the captured panel sits below the question rather than beside it,
// which is the right order: you answer, then you scroll a little and see what
// was taken from the answer.
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
const keyInterests = ref([])

const question = computed(() => questions.value.find((q) => q.id === stepId.value) || null)
const position = computed(() => questions.value.findIndex((q) => q.id === stepId.value) + 1)
const progress = computed(() =>
  questions.value.length ? Math.round((answered.value.length / questions.value.length) * 100) : 0
)

// Something worth showing on the captured panel: until the first answer lands
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
  if (res.key_interests) keyInterests.value = res.key_interests
}

async function focusBox() {
  await nextTick()
  // Autofocus pops the keyboard the instant the page opens on a phone, which
  // hides the question you are meant to be reading. Pointer devices only.
  if (window.matchMedia('(pointer: fine)').matches) box.value?.focus()
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
    stepId.value = res.next_step || null
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

const WRITE_LABELS = {
  add_travel_history: 'Been there',
  add_wishlist: 'Want to go',
  set_passports: 'Passport',
  set_interests: 'Into',
  set_key_interests: 'Really into',
  set_social_style: 'Travelling',
  update_profile: 'Noted'
}

const FIELD_LABELS = {
  budget_band: 'Budget',
  travel_style: 'Pace',
  climate_preference: 'Climate',
  current_location: 'Currently in'
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
    case 'set_key_interests':
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
</script>

<template>
  <div class="page">
    <div v-if="loading" class="panel loading muted">Getting things ready…</div>

    <template v-else>
      <header class="intro">
        <h1 class="grad-text">Welcome to Travel Steezy</h1>
        <p class="muted">
          Five questions, answered however you like — full sentences, a scribbled list,
          whatever comes out. I will turn it into a profile you can edit, and then I
          never have to ask you any of it again.
        </p>
      </header>

      <!-- ------------------------------------------------------- progress -->
      <div class="rail">
        <div class="bar"><div class="fill" :style="{ width: `${progress}%` }" /></div>
        <ol class="steps">
          <li
            v-for="(q, index) in questions"
            :key="q.id"
            :class="{
              done: answered.includes(q.id),
              current: q.id === stepId,
              clickable: answered.includes(q.id)
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
          <!-- -------------------------------------------- the question -->
          <section v-if="question" :key="stepId" class="panel ask">
            <p class="step">Question {{ position }} of {{ questions.length }}</p>
            <h2>{{ question.title }}</h2>
            <p class="prompt">{{ question.prompt }}</p>
            <p class="muted small hint">{{ question.hint }}</p>

            <textarea
              ref="box"
              v-model="answer"
              rows="5"
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
            <div v-if="error" class="error soft">{{ error }}</div>

            <button class="ghost small bail" :disabled="busy" @click="skipAll">
              Skip all of this and go straight to the chat
            </button>
          </section>

          <!-- ------------------------------------------ the review step -->
          <section v-else key="done" class="panel ask done-panel">
            <h2>That is your profile built</h2>
            <p class="muted">
              Everything below is stored against your account and read before every
              answer you get. Check it over — anything that came out wrong is fixable
              now, and any time after, on the Trip page.
            </p>
            <div v-if="error" class="error soft">{{ error }}</div>
            <div class="actions">
              <button class="primary" :disabled="busy" @click="finish">Start exploring</button>
              <RouterLink class="link small" to="/preferences">Edit it in full first</RouterLink>
            </div>
            <p class="muted small revisit">
              Want to redo an answer? Tap any completed step above.
            </p>
          </section>
        </Transition>

        <!-- ------------------------------------------ what was captured -->
        <aside class="panel captured">
          <h3>What I have so far</h3>

          <Transition name="pop">
            <div v-if="justCaptured.length" class="just">
              <p class="eyebrow fresh">From that answer</p>
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
              <p class="eyebrow">Been to</p>
              <ul class="places">
                <li v-for="stop in history" :key="stop.location">
                  <span class="place grow">{{ stop.location }}</span>
                  <StarRating v-if="stop.rating" :model-value="stop.rating" readonly />
                </li>
              </ul>
            </div>

            <div v-if="wishlist.length" class="group">
              <p class="eyebrow">Want to go</p>
              <ul class="places">
                <li v-for="item in wishlist" :key="item.location">
                  <span class="place grow">{{ item.location }}</span>
                  <span class="tag" :class="{ go: item.priority === 1 }">
                    {{ item.revisit ? 'again' : priorityLabel(item.priority) }}
                  </span>
                </li>
              </ul>
            </div>

            <div v-if="(profile.passports || []).length" class="group">
              <p class="eyebrow">Passport{{ profile.passports.length > 1 ? 's' : '' }}</p>
              <div class="chips">
                <span v-for="p in profile.passports" :key="p" class="tag">{{ p }}</span>
              </div>
            </div>

            <div
              v-if="profile.budget_band || profile.travel_style || profile.climate_preference || profile.social_style || profile.current_location"
              class="group"
            >
              <p class="eyebrow">How you travel</p>
              <dl>
                <template v-if="profile.budget_band"><dt>Budget</dt><dd>{{ labelFor(profile.budget_band) }}</dd></template>
                <template v-if="profile.travel_style"><dt>Pace</dt><dd>{{ labelFor(profile.travel_style) }}</dd></template>
                <template v-if="profile.climate_preference"><dt>Climate</dt><dd>{{ labelFor(profile.climate_preference) }}</dd></template>
                <template v-if="profile.social_style"><dt>Company</dt><dd>{{ labelFor(profile.social_style) }}</dd></template>
                <template v-if="profile.current_location"><dt>Currently in</dt><dd>{{ profile.current_location }}</dd></template>
              </dl>
            </div>

            <div v-if="interests.length" class="group">
              <p class="eyebrow">Into</p>
              <div class="chips">
                <span
                  v-for="i in interests"
                  :key="i"
                  class="tag"
                  :class="{ key: keyInterests.includes(i) }"
                >
                  <span v-if="keyInterests.includes(i)" class="star" aria-hidden="true">★</span>{{ i }}
                </span>
              </div>
            </div>
          </template>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.loading { text-align: center; padding: var(--sp-10) var(--sp-5); }

.intro { text-align: center; animation: fadeInUp var(--dur-slow) var(--ease-out) both; }
.intro h1 { margin: 0 0 var(--sp-2); font-size: var(--fs-h1); }
.intro p { margin: 0 auto; max-width: 58ch; font-size: 14px; }

/* ---------------------------------------------------------------- progress */
.rail { margin-top: calc(-1 * var(--sp-1)); }
.bar { height: 4px; background: var(--line); border-radius: var(--radius-pill); overflow: hidden; }
.fill {
  height: 100%;
  background: var(--accent-grad);
  background-size: 200% 100%;
  border-radius: var(--radius-pill);
  transition: width var(--dur-slow) var(--ease-out);
  animation: shimmer 2.5s linear infinite;
}

.steps {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-2);
  list-style: none;
  margin: var(--sp-3) 0 0;
  padding: 0;
}
.steps li {
  display: flex; align-items: center; gap: 7px;
  font-size: 12.5px; color: var(--muted); min-width: 0;
  transition: color var(--dur) ease;
}
.steps li.clickable { cursor: pointer; }
.steps li.done .pip { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
.steps li.current { color: var(--text); }
.steps li.current .pip { border-color: var(--accent); color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.pip {
  display: grid;
  place-items: center;
  flex: none;
  width: 22px; height: 22px;
  border: 1px solid var(--line);
  border-radius: 50%;
  font-size: 11px;
  font-weight: 600;
  transition: transform var(--dur-fast) var(--ease-spring), box-shadow var(--dur) ease;
}
@media (hover: hover) {
  .steps li.clickable:hover .name { color: var(--text); }
  .steps li.clickable:hover .pip { transform: scale(1.12); }
}
.name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* On a phone the step names cannot all fit, so the rail becomes pips only -
   still showing where you are and what is left, without five truncated words. */
@media (max-width: 760px) {
  .steps { justify-content: center; gap: var(--sp-3); }
  .steps .name { display: none; }
  .steps li.clickable .pip { width: 30px; height: 30px; font-size: 12px; }
  .steps li .pip { width: 30px; height: 30px; font-size: 12px; }
}

/* ------------------------------------------------------------------ layout
   The whole page is locked to the space main actually gives it (--view-h,
   minus the gutter main pads it with) and never scrolls itself. .cols takes
   whatever is left after the intro and the rail, and its two panels each
   scroll their own overflow — a laptop-height window scrolls the question
   or the captured list, never the page underneath them. */
.page { height: calc(var(--view-h) - 2 * var(--gutter)); overflow: hidden; }

.cols {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: var(--sp-4);
  align-items: stretch;
  flex: 1;
  min-height: 0;
}
@media (max-width: 900px) {
  .cols { display: flex; flex-direction: column; min-height: 0; }
}

/* ---------------------------------------------------------------- question */
.step {
  margin: 0 0 var(--sp-1);
  letter-spacing: .06em;
  text-transform: uppercase;
  font-size: var(--fs-xs);
  font-weight: 650;
  color: var(--accent-bright);
}
.ask { min-height: 0; overflow-y: auto; }
@media (max-width: 900px) { .ask { flex: 1 1 auto; } }
.ask h2 { margin: 0 0 var(--sp-2); font-size: var(--fs-h2); }
.prompt { margin: 0 0 var(--sp-1); font-size: 14.5px; }
.hint { margin: 0 0 var(--sp-4); }

textarea { min-height: 118px; }

.actions { display: flex; align-items: center; gap: var(--sp-3); flex-wrap: wrap; margin-top: var(--sp-4); }
.actions > button:first-child { flex: 1 1 auto; min-width: 130px; }
.shortcut { margin-left: auto; }
.link { color: var(--accent); text-decoration: none; font-weight: 550; }

.soft { margin: var(--sp-4) 0 0; }
.bail {
  display: block;
  width: 100%;
  margin: var(--sp-5) 0 0;
  color: var(--muted);
  border: none;
  font-size: 12.5px;
}
.bail:hover { color: var(--text); }

.done-panel h2 { margin-bottom: var(--sp-2); }
.done-panel p { font-size: 14px; }
.revisit { margin: var(--sp-4) 0 0; }

/* ---------------------------------------------------------------- captured */
.captured { min-height: 0; overflow-y: auto; }
@media (max-width: 900px) { .captured { flex: 0 1 auto; max-height: 38vh; } }
.captured h3 { margin: 0 0 var(--sp-3); font-size: var(--fs-h3); }

.just {
  background: var(--moss-soft);
  border: 1px solid var(--moss-dim);
  border-radius: var(--radius-sm);
  padding: var(--sp-3);
  margin-bottom: var(--sp-4);
  box-shadow: var(--glow-moss);
}
.eyebrow.fresh { color: var(--moss-bright); }
.just ul { margin: 0; padding: 0; list-style: none; }
.just li { display: flex; gap: var(--sp-2); font-size: var(--fs-sm); margin-bottom: var(--sp-1); }
.just li:last-child { margin-bottom: 0; }
.op { flex: none; color: var(--moss-bright); font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: .04em; padding-top: 2px; }
.what { color: var(--text); word-break: break-word; }

.group { margin-bottom: var(--sp-4); }
.group:last-child { margin-bottom: 0; }

.places { list-style: none; margin: 0; padding: 0; }
.places li { display: flex; align-items: center; gap: var(--sp-2); font-size: 13.5px; margin-bottom: 5px; }
.place { text-transform: capitalize; min-width: 0; }

.chips { display: flex; flex-wrap: wrap; gap: 5px; }
.tag.key { border-color: var(--accent); background: var(--accent-soft); color: var(--text); font-weight: 600; }
.tag .star { font-size: 12px; line-height: 1; margin-right: 3px; }

dl { display: grid; grid-template-columns: minmax(72px, auto) 1fr; gap: var(--sp-1) var(--sp-3); margin: 0; font-size: 13.5px; }
dt { color: var(--muted); }
dd { margin: 0; word-break: break-word; }

.empty { margin: 0; }
</style>
