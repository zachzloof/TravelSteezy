<script setup>
// Post-visit review prompt. Appears when the backend says a place is due one,
// either because the traveller left it or because they have not mentioned it in
// a few days. Answering it writes to travel_history and feeds the RAG store.
import { ref } from 'vue'

const props = defineProps({
  location: { type: String, required: true },
  busy: { type: Boolean, default: false }
})
const emit = defineEmits(['submit', 'dismiss'])

const rating = ref(0)
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
      <button class="ghost small" @click="emit('dismiss')">Not now</button>
    </div>

    <div class="stars" role="radiogroup" :aria-label="`Rating for ${location}`">
      <button
        v-for="n in 5"
        :key="n"
        class="star"
        :class="{ on: n <= rating }"
        role="radio"
        :aria-checked="n === rating"
        :aria-label="`${n} out of 5`"
        @click="rating = n"
      >★</button>
      <span v-if="rating" class="muted small">{{ rating }}/5</span>
    </div>

    <textarea
      v-model="notes"
      rows="2"
      placeholder="What was it actually like? Anything another backpacker should know."
    />

    <label class="share small">
      <input v-model="share" type="checkbox" />
      Share anonymously to help other travellers
    </label>

    <button class="primary" :disabled="busy || (!rating && !notes.trim())" @click="submit">
      {{ busy ? 'Saving…' : 'Save review' }}
    </button>
  </div>
</template>

<style scoped>
.review { border-color: var(--accent-dim); }
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
h4 { margin: 0; font-size: 14px; text-transform: capitalize; }

.stars { display: flex; align-items: center; gap: 3px; margin-bottom: 10px; }
.star {
  border: none;
  background: none;
  color: var(--line);
  font-size: 22px;
  padding: 0 2px;
  line-height: 1;
}
.star.on { color: var(--warn); }
.star:hover { color: var(--warn); }
.stars .small { margin-left: 8px; }

textarea { margin-bottom: 10px; }

.share {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 12px;
  color: var(--muted);
}
.share input { width: auto; }
</style>
