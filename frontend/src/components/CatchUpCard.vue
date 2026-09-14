<script setup>
// "Here's where we left off - what's changed?"
//
// Shown once per calendar-day gap since the account's last real chat message.
// Deliberately not a conversation the way the old onboarding flow was: one
// fixed card, one free-text box, and a one-tap "still here" button that costs
// no model call at all. Typing an answer is processed as an ordinary chat
// turn (see ChatView), so it picks up visits/departures/wishlist/reviews for
// free - it is not a second extraction path.
import { computed, ref } from 'vue'

const props = defineProps({
  summary: { type: String, default: '' },
  daysSince: { type: Number, default: null },
  busy: { type: Boolean, default: false }
})
const emit = defineEmits(['update', 'dismiss'])

const text = ref('')

const heading = computed(() => {
  if (!props.daysSince) return 'Welcome back'
  return `Welcome back — it's been ${props.daysSince === 1 ? 'a day' : `${props.daysSince} days`}`
})

function submit() {
  if (!text.value.trim() || props.busy) return
  emit('update', text.value.trim())
  text.value = ''
}
</script>

<template>
  <div class="catchup panel">
    <div class="head">
      <h4>{{ heading }}</h4>
      <button class="icon-btn" aria-label="Dismiss" title="Dismiss" @click="emit('dismiss')">×</button>
    </div>

    <p v-if="summary" class="summary">{{ summary }}</p>
    <p class="prompt muted small">What's changed since then?</p>

    <textarea
      v-model="text"
      rows="2"
      placeholder="Left Chiang Mai, spent a few days in Pai, heading to Laos next…"
      :disabled="busy"
      @keydown.enter.exact.prevent="submit"
    />

    <div class="actions">
      <button class="primary" :disabled="busy || !text.trim()" @click="submit">
        {{ busy ? 'Updating…' : 'Update me' }}
      </button>
      <button class="ghost small" :disabled="busy" @click="emit('dismiss')">
        Nothing's changed
      </button>
    </div>
  </div>
</template>

<style scoped>
.catchup { border-color: var(--accent-dim); box-shadow: var(--glow-accent); }

.head { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); margin-bottom: var(--sp-2); }
h4 { margin: 0; font-size: var(--fs-h3); }

.summary { margin: 0 0 var(--sp-1); font-size: 13.5px; }
.prompt { margin: 0 0 var(--sp-3); }

textarea { margin-bottom: var(--sp-3); }

/* The two buttons sit side by side where there is room, and stack rather than
   shrink the primary action to an unreadable width on a narrow phone. */
.actions { display: flex; align-items: center; gap: var(--sp-3); flex-wrap: wrap; }
.actions button { flex: 1 1 auto; min-width: 140px; }
</style>
