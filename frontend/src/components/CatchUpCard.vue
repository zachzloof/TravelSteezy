<script setup>
// "Here's where we left off - what's changed?"
//
// Shown once per calendar-day gap since the account's last real chat message.
// Deliberately not a conversation the way the old onboarding flow was: one
// fixed card, one free-text box, and a one-tap "still here" button that costs
// no model call at all. Typing an answer is processed as an ordinary chat
// turn (see ChatView), so it picks up visits/departures/wishlist/reviews for
// free - it is not a second extraction path.
import { ref } from 'vue'

const props = defineProps({
  summary: { type: String, default: '' },
  daysSince: { type: Number, default: null },
  busy: { type: Boolean, default: false }
})
const emit = defineEmits(['update', 'dismiss'])

const text = ref('')

function submit() {
  if (!text.value.trim() || props.busy) return
  emit('update', text.value.trim())
  text.value = ''
}
</script>

<template>
  <div class="catchup panel">
    <div class="head">
      <h4>Welcome back{{ daysSince ? ` — it's been ${daysSince === 1 ? 'a day' : `${daysSince} days`}` : '' }}</h4>
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
        Still here, nothing's changed
      </button>
    </div>
  </div>
</template>

<style scoped>
.catchup { border-color: var(--accent-dim); box-shadow: var(--glow-accent); }
.head { margin-bottom: 8px; }
h4 { margin: 0; font-size: 14px; }

.summary { margin: 0 0 6px; font-size: 13.5px; }
.prompt { margin: 0 0 10px; }

textarea { margin-bottom: 10px; }

.actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
</style>
