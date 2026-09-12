<script setup>
// The route and wishlist, shown live in the chat sidebar. Backed by /travel/me,
// the same rows the agents query, so "it remembered where I went" is visible
// rather than merely claimed in a reply.
import { computed } from 'vue'
import StarRating from './StarRating.vue'

const props = defineProps({
  history: { type: Array, default: () => [] },
  wishlist: { type: Array, default: () => [] },
  interests: { type: Array, default: () => [] }
})
const emit = defineEmits(['drop-wishlist'])

const PRIORITY = { 1: 'high', 2: 'medium', 3: 'low' }

// Newest first: the most recent stops are the ones worth seeing at a glance.
const route = computed(() => [...props.history].reverse())
</script>

<template>
  <section class="trip">
    <h4>Route so far</h4>
    <ol v-if="route.length" class="route">
      <li v-for="entry in route" :key="entry.location">
        <span class="dot" :class="{ rated: entry.rating }" />
        <div class="body">
          <span class="place">{{ entry.location }}</span>
          <StarRating v-if="entry.rating" :model-value="entry.rating" readonly />
          <div v-if="entry.review_notes" class="muted small note">{{ entry.review_notes }}</div>
          <div class="muted small meta">
            <span v-if="entry.country">{{ entry.country }}</span>
            <span v-if="entry.source === 'tracked'" class="tracked">auto-logged</span>
          </div>
        </div>
      </li>
    </ol>
    <p v-else class="muted small">Nothing logged yet.</p>

    <h4>Want to go</h4>
    <TransitionGroup v-if="wishlist.length" tag="ul" name="fade-slide" class="wish">
      <li v-for="item in wishlist" :key="item.location">
        <span class="place">{{ item.location }}</span>
        <span class="tag" :class="{ go: item.priority === 1 }">
          {{ item.revisit ? 'again' : PRIORITY[item.priority] }}
        </span>
        <button
          class="ghost drop"
          :title="`Remove ${item.location}`"
          @click="emit('drop-wishlist', item.location)"
        >×</button>
      </li>
    </TransitionGroup>
    <p v-else class="muted small">Nothing on the wishlist.</p>

    <template v-if="interests.length">
      <h4>Interests</h4>
      <div class="chips">
        <span v-for="i in interests" :key="i" class="tag">{{ i }}</span>
      </div>
    </template>

    <RouterLink class="manage small" to="/preferences">
      Rate a stop or edit this list →
    </RouterLink>
  </section>
</template>

<style scoped>
.trip { margin-top: 18px; border-top: 1px solid var(--line); padding-top: 14px; }

h4 {
  margin: 0 0 8px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--muted);
}
h4:not(:first-child) { margin-top: 16px; }

.route { list-style: none; margin: 0; padding: 0; }
.route li { display: flex; gap: 9px; padding-bottom: 10px; position: relative; }
.route li:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 13px;
  bottom: 0;
  width: 1px;
  background: var(--line);
}
.dot {
  width: 9px; height: 9px;
  border-radius: 50%;
  background: var(--line);
  border: 1px solid var(--muted);
  margin-top: 4px;
  flex: none;
  z-index: 1;
  transition: box-shadow var(--dur) ease;
}
.dot.rated { background: var(--accent); border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }

.body { min-width: 0; }
.place { font-size: 13.5px; text-transform: capitalize; margin-right: 6px; }
.note { font-style: italic; word-break: break-word; }
.meta { display: flex; gap: 8px; text-transform: capitalize; }
.tracked { color: var(--accent-dim); text-transform: none; }

.wish { list-style: none; margin: 0; padding: 0; }
.wish li { display: flex; align-items: center; gap: 7px; margin-bottom: 6px; font-size: 13.5px; }
.wish .place { flex: 1; }
.drop {
  border: none; background: none; color: var(--muted);
  padding: 0 4px; font-size: 16px; line-height: 1;
}
.drop:hover { color: var(--bad); }

.chips { display: flex; flex-wrap: wrap; gap: 5px; }

.manage {
  display: inline-block;
  margin-top: 14px;
  color: var(--accent);
  text-decoration: none;
  transition: transform var(--dur-fast) ease, color var(--dur-fast) ease;
}
.manage:hover { color: var(--accent-bright); transform: translateX(2px); }
</style>
