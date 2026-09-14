<script setup>
// Shows what the assistant currently remembers for THIS account, read from
// GET /profile/me. It is deliberately the same data the agents are hydrated
// with, so "it remembers me" is visible rather than merely claimed in the chat
// reply.
//
// Two things it deliberately does NOT show:
//
//   Visited this trip — the country-level departure log. It was a second,
//     shorter list sitting directly above the route, showing the same journey
//     at a coarser grain. Route so far covers it. The departure log is still
//     editable on the Trip page, where logging one is an explicit action.
//   Interests — the free-text mirror column. TripPanel renders the real
//     weighted interest rows just below, so this was the same answer twice.
import { computed } from 'vue'
import { labelFor } from '../preferences'

const props = defineProps({
  profile: { type: Object, default: null },
  // Inside the mobile sheet the surrounding chrome already exists, so the
  // panel border and padding would be a box drawn inside a box.
  flat: { type: Boolean, default: false },
  // Desktop rail only: hides everything below the toolbar so the collapsed
  // rail is just that sticky bar. Mobile's flat instance never sets this.
  collapsed: { type: Boolean, default: false }
})

const FIELDS = [
  ['nationality', 'Passport'],
  ['current_location', 'Currently in'],
  ['budget_band', 'Budget'],
  ['travel_style', 'Pace'],
  ['climate_preference', 'Climate']
]

// Stored values are enum keys ("mid", "very_slow"). Showing the label the user
// actually picked - "Mid-range", "Very slow" - is the difference between this
// reading as your profile and reading as a database dump.
const rows = computed(() => {
  const p = props.profile || {}
  return FIELDS.map(([key, label]) => ({
    key,
    label,
    value: p[key] ? labelFor(p[key]) : ''
  }))
})

const filled = computed(() => rows.value.filter((r) => r.value).length)
</script>

<template>
  <div :class="[flat ? 'context flat' : 'context panel', { collapsed }]">
    <!-- Sticky inside the panel's own scroll area, so it never adds height
         beyond the panel's max-height - only the desktop rail passes this. -->
    <div v-if="$slots.toolbar" class="toolbar">
      <slot name="toolbar" />
    </div>

    <Transition name="mem-body">
      <div v-show="!collapsed" class="body">
        <header v-if="!flat" class="head">
          <h3>What I remember</h3>
          <span class="muted small">{{ filled }}/{{ rows.length }}</span>
        </header>
        <p v-if="!flat" class="muted small sub">Stored against your account, not this browser.</p>

        <dl>
          <template v-for="row in rows" :key="row.key">
            <dt>{{ row.label }}</dt>
            <dd :class="{ unknown: !row.value }">{{ row.value || 'not set' }}</dd>
          </template>
          <template v-if="profile?.visa_deadline_date">
            <dt>Deadline</dt>
            <dd class="deadline">
              {{ profile.visa_deadline_date }}
              <span v-if="profile.visa_deadline_note" class="muted">— {{ profile.visa_deadline_note }}</span>
            </dd>
          </template>
        </dl>

        <!-- The trip panel (route, wishlist, interests) is slotted in here. -->
        <slot />

        <RouterLink class="edit small" to="/preferences">Edit my trip profile →</RouterLink>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* Bounded to the same height the chat column fits into, so a fully-populated
   sidebar scrolls internally on a short (laptop) viewport instead of stretching
   the row and forcing the whole page to scroll for its sake. Padding moves onto
   .toolbar/.body below so the sticky toolbar can sit flush with the panel's own
   edges rather than adding height on top of them. */
.context.panel {
  animation: fadeIn var(--dur-slow) var(--ease-out) both;
  display: flex;
  flex-direction: column;
  max-height: calc(var(--view-h) - 2 * var(--gutter));
  padding: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.toolbar {
  position: sticky;
  top: 0;
  z-index: 1;
  flex: none;
  display: flex;
  justify-content: flex-end;
  padding: var(--sp-2) var(--sp-3);
  background: var(--panel);
}
.context.collapsed .toolbar { justify-content: center; padding: var(--sp-2); }

.body { min-width: 0; }
.context.panel .body { padding: var(--sp-2) var(--sp-5) var(--sp-5); }
@media (max-width: 560px) {
  .context.panel .body { padding: var(--sp-2) var(--sp-4) var(--sp-4); }
}

.mem-body-enter-active,
.mem-body-leave-active { transition: opacity var(--dur) ease; }
.mem-body-enter-from,
.mem-body-leave-to { opacity: 0; }

.head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-2); }
h3 { margin: 0 0 2px; font-size: var(--fs-h3); }
.sub { margin: 0 0 var(--sp-4); }

/* auto-fit label column: long labels do not force the value onto its own line,
   short ones do not leave a gap. */
dl {
  display: grid;
  grid-template-columns: minmax(72px, auto) 1fr;
  gap: 6px var(--sp-3);
  margin: 0;
  font-size: 13.5px;
  align-items: baseline;
}
dt { color: var(--muted); }
dd { margin: 0; word-break: break-word; }
dd.unknown { color: var(--muted-2); font-style: italic; }
dd.deadline { color: var(--warn); }

.edit {
  display: inline-block;
  margin-top: var(--sp-4);
  padding: 10px 0;
  color: var(--accent);
  text-decoration: none;
  font-weight: 550;
  transition: transform var(--dur-fast) ease, color var(--dur-fast) ease;
}
.edit:hover { color: var(--accent-bright); transform: translateX(2px); }
</style>
