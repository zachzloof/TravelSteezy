<script setup>
// Post-visit review prompt. Appears when the backend says a place is due one,
// either because the traveller left it or because they have not mentioned it in
// a few days. Answering it writes to travel_history and feeds the RAG store.
//
// The stars are StarRating rather than a second hand-rolled row, so tapping the
// same star twice clears the rating here exactly like it does everywhere else.
import { ref } from 'vue'
import StarRating from './StarRating.vue'

const props = defineProps({
  location: { type: String, required: true },
  busy: { type: Boolean, default: false }
})
const emit = defineEmits(['submit', 'dismiss'])

const rating = ref(null)
const notes = ref('')
const share = ref(true)

function submit() {
  if (!rating.value && !notes.value.trim()) return
  emit('submit', {
    location: props.location,
    rating: rating.value || null,
    notes: notes.value.trim() || null,
    share: share.value
  })
}
</script>

<template>
  <div class="review panel">
    <div class="head">
      <h4>How was {{ location }}?</h4>
      <button class="icon-btn" aria-label="Not now" title="Not now" @click="emit('dismiss')">×</button>
    </div>

    <StarRating
      v-model="rating"
      size="lg"
      :show-hint="false"
      :label="`Rating for ${location}`"
      class="stars"
    />

    <textarea
      v-model="notes"
      rows="2"
      placeholder="What was it actually like? Anything another backpacker should know."
    />

    <label class="share small">
      <input v-model="share" type="checkbox" />
      <span>Share anonymously to help other travellers</span>
    </label>

    <button class="primary full" :disabled="busy || (!rating && !notes.trim())" @click="submit">
      {{ busy ? 'Saving…' : 'Save review' }}
    </button>
  </div>
</template>

<style scoped>
.review { border-color: var(--accent-dim); box-shadow: var(--glow-accent); }

.head { display: flex; justify-content: space-between; align-items: center; gap: var(--sp-2); margin-bottom: var(--sp-2); }
h4 { margin: 0; font-size: var(--fs-h3); text-transform: capitalize; }

.stars { margin-bottom: var(--sp-3); }

textarea { margin-bottom: var(--sp-3); }

.share {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin-bottom: var(--sp-4);
  color: var(--muted);
  cursor: pointer;
}
.share input { width: 17px; height: 17px; flex: none; accent-color: var(--accent); }
</style>
