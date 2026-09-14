<script setup>
// The route and wishlist, shown live in the chat sidebar. Backed by /travel/me,
// the same rows the agents query, so "it remembered where I went" is visible
// rather than merely claimed in a reply.
//
// The "edit this list" link that used to sit at the bottom is gone: the panel
// this is slotted into already links to the same page, and two links to
// /preferences a few centimetres apart is just noise.
import { computed } from 'vue'
import StarRating from './StarRating.vue'

const props = defineProps({
  history: { type: Array, default: () => [] },
  wishlist: { type: Array, default: () => [] },
  interests: { type: Array, default: () => [] }
})
const emit = defineEmits(['drop-wishlist'])

const PRIORITY = { 1: 'high', 2: 'medium', 3: 'low' }

// A country-level stop stores the same string in both fields, which rendered as
// "Vietnam" with "Vietnam" underneath it.
const showCountry = (entry) =>
  entry.country && entry.country.toLowerCase() !== entry.location.toLowerCase()

// Newest first: the most recent stops are the ones worth seeing at a glance.
const route = computed(() => [...props.history].reverse())
</script>

<template>
  <section class="trip">
    <div class="group">
      <div class="group-head">
        <p class="eyebrow">Route so far</p>
        <span v-if="route.length" class="muted small">{{ route.length }}</span>
      </div>
      <ol v-if="route.length" class="route">
        <li v-for="entry in route" :key="entry.location">
          <span class="dot" :class="{ rated: entry.rating }" />
          <div class="body">
            <div class="line">
              <span class="place">{{ entry.location }}</span>
              <StarRating v-if="entry.rating" :model-value="entry.rating" readonly />
            </div>
            <div v-if="entry.review_notes" class="muted small note">{{ entry.review_notes }}</div>
            <div v-if="showCountry(entry) || entry.source === 'tracked'" class="muted small meta">
              <span v-if="showCountry(entry)">{{ entry.country }}</span>
              <span v-if="entry.source === 'tracked'" class="tracked">auto-logged</span>
            </div>
          </div>
        </li>
      </ol>
      <p v-else class="muted small none">Nothing logged yet.</p>
    </div>

    <div class="group">
      <div class="group-head">
        <p class="eyebrow">Want to go</p>
        <span v-if="wishlist.length" class="muted small">{{ wishlist.length }}</span>
      </div>
      <TransitionGroup v-if="wishlist.length" tag="ul" name="fade-slide" class="wish">
        <li v-for="item in wishlist" :key="item.location">
          <span class="place grow">{{ item.location }}</span>
          <span class="tag" :class="{ go: item.priority === 1 }">
            {{ item.revisit ? 'again' : PRIORITY[item.priority] }}
          </span>
          <button
            class="icon-btn destructive"
            :title="`Remove ${item.location}`"
            :aria-label="`Remove ${item.location}`"
            @click="emit('drop-wishlist', item.location)"
          >×</button>
        </li>
      </TransitionGroup>
      <p v-else class="muted small none">Nothing on the wishlist.</p>
    </div>

    <div v-if="interests.length" class="group">
      <p class="eyebrow">Interests</p>
      <div class="chips">
        <span v-for="i in interests" :key="i" class="tag">{{ i }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.trip { margin-top: var(--sp-5); border-top: 1px solid var(--line); padding-top: var(--sp-4); }

.group { margin-bottom: var(--sp-5); }
.group:last-child { margin-bottom: 0; }
.group-head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-2); }

.none { margin: 0; }

/* ------------------------------------------------------------------- route */
.route { list-style: none; margin: 0; padding: 0; }
.route li { display: flex; gap: 10px; padding-bottom: var(--sp-3); position: relative; }
.route li:last-child { padding-bottom: 0; }
.route li:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 14px;
  bottom: 2px;
  width: 1px;
  background: var(--line);
}
.dot {
  width: 9px; height: 9px;
  border-radius: 50%;
  background: var(--stone-700);
  border: 1px solid var(--muted-2);
  margin-top: 5px;
  flex: none;
  z-index: 1;
}
.dot.rated { background: var(--accent); border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }

.body { min-width: 0; flex: 1; }
.line { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
.place { font-size: 13.5px; text-transform: capitalize; }
.note { font-style: italic; word-break: break-word; margin-top: 2px; }
.meta { display: flex; gap: var(--sp-2); text-transform: capitalize; margin-top: 2px; }
.tracked { color: var(--muted-2); text-transform: none; }

/* ---------------------------------------------------------------- wishlist */
.wish { list-style: none; margin: 0; padding: 0; }
.wish li {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: 13.5px;
  padding: 3px 0;
}
.wish .place { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.chips { display: flex; flex-wrap: wrap; gap: 5px; }
</style>
