<script setup>
// "Report a bug", available on every page once logged in. It only ever asks the
// traveller what went wrong - no screenshot, no diagnostics to fill in - and
// lets the backend assemble the actual trace (recent conversation + Langfuse
// link) from server-side state. See backend/routers/bugs.py.
//
// This used to own a floating action button in the bottom-right corner. On a
// phone that is exactly where the chat composer's send button is, so the two
// overlapped and the bug button sat on top of the primary action of the whole
// app. It is now opened from the account menu instead, and this component is
// just the dialog: the parent holds a ref and calls show().
import { ref, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { api, lastTrace } from '../api'

const route = useRoute()

const open = ref(false)
const description = ref('')
const busy = ref(false)
const error = ref('')
const sent = ref(false)

function show() {
  open.value = true
  sent.value = false
  error.value = ''
}

function close() {
  if (busy.value) return
  open.value = false
  description.value = ''
}

defineExpose({ show })

function onKeydown(event) {
  if (event.key === 'Escape') close()
}

watch(open, (isOpen) => {
  document.body.style.overflow = isOpen ? 'hidden' : ''
  if (isOpen) window.addEventListener('keydown', onKeydown)
  else window.removeEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  document.body.style.overflow = ''
  window.removeEventListener('keydown', onKeydown)
})

async function submit() {
  const text = description.value.trim()
  if (!text || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await api.reportBug({
      description: text,
      page: route.fullPath,
      user_agent: navigator.userAgent,
      trace_id: lastTrace.id
    })
    sent.value = true
    description.value = ''
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="overlay" @click.self="close">
        <div class="dialog panel" role="dialog" aria-modal="true" aria-label="Report a bug">
          <template v-if="!sent">
            <h3>Report a bug</h3>
            <p class="muted small">
              What went wrong? No need for a screenshot — this grabs your recent
              conversation automatically.
            </p>
            <textarea
              v-model="description"
              rows="4"
              autofocus
              placeholder="e.g. I asked about visas for Vietnam and it said I needed a visa on arrival, but I'm actually a UK passport holder who doesn't."
            />
            <div v-if="error" class="error msg">{{ error }}</div>
            <div class="actions">
              <button class="ghost" :disabled="busy" @click="close">Cancel</button>
              <button class="primary" :disabled="busy || !description.trim()" @click="submit">
                {{ busy ? 'Sending…' : 'Send report' }}
              </button>
            </div>
          </template>
          <template v-else>
            <h3>Thanks!</h3>
            <p class="muted small">
              Your report was sent. It's saved with your recent conversation so it can be fixed
              without you having to explain everything again.
            </p>
            <div class="actions">
              <button class="primary" @click="close">Done</button>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: var(--sp-4);
  background: rgba(0, 0, 0, .55);
  backdrop-filter: blur(3px);
}

.dialog {
  width: 100%;
  max-width: 460px;
  max-height: calc(100dvh - 2 * var(--sp-4));
  overflow-y: auto;
  padding: var(--sp-5);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}
h3 { margin: 0 0 var(--sp-1); font-size: var(--fs-lg); }
p { margin: 0 0 var(--sp-3); }
textarea { margin-bottom: var(--sp-3); }
.msg { margin-bottom: var(--sp-3); }

/* Full-width stacked buttons on a phone: two small right-aligned buttons in a
   modal are the easiest thing in the app to mis-tap. */
.actions { display: flex; justify-content: flex-end; gap: var(--sp-2); }
@media (max-width: 560px) {
  .actions { flex-direction: column-reverse; }
  .actions button { width: 100%; }
}
</style>
