<script setup>
// A floating "report a bug" affordance available on every page once logged
// in. It only ever asks the traveller what went wrong - no screenshot, no
// diagnostics to fill in - and lets the backend assemble the actual trace
// (recent conversation + Langfuse link) from server-side state. See
// backend/routers/bugs.py.
import { ref } from 'vue'
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
  <button class="fab" title="Report a bug" @click="show">🐞</button>

  <Transition name="fade">
    <div v-if="open" class="overlay" @click.self="close">
      <div class="dialog panel">
        <template v-if="!sent">
          <h3>Report a bug</h3>
          <p class="muted small">
            What went wrong? No need for a screenshot - this grabs your recent
            conversation automatically.
          </p>
          <textarea
            v-model="description"
            rows="4"
            autofocus
            placeholder="e.g. I asked about visas for Vietnam and it said I needed a visa on arrival, but I'm actually a UK passport holder who doesn't."
          />
          <div v-if="error" class="error">{{ error }}</div>
          <div class="actions">
            <button class="ghost small" :disabled="busy" @click="close">Cancel</button>
            <button class="primary small" :disabled="busy || !description.trim()" @click="submit">
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
            <button class="primary small" @click="close">Done</button>
          </div>
        </template>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.fab {
  position: fixed;
  right: clamp(14px, 3vw, 28px);
  bottom: clamp(14px, 3vw, 28px);
  z-index: 30;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 20px;
  background: var(--panel);
  box-shadow: var(--shadow-md);
}
.fab:hover:not(:disabled) { transform: translateY(-2px) scale(1.06); }

.overlay {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgba(0, 0, 0, .5);
  backdrop-filter: blur(2px);
}

.dialog {
  width: 100%;
  max-width: 440px;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}
h3 { margin: 0 0 4px; font-size: 17px; }
p { margin: 0 0 12px; }
textarea { margin-bottom: 10px; }

.actions { display: flex; justify-content: flex-end; gap: 8px; }

.fade-enter-active, .fade-leave-active { transition: opacity var(--dur-fast) ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
