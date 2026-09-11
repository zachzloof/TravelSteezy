<script setup>
// Shows what the assistant currently remembers for THIS account, read from
// GET /profile/me. It is deliberately the same data the agents are hydrated with,
// so "it remembers me" is visible rather than merely claimed in the chat reply.
defineProps({
  profile: { type: Object, default: null },
  visited: { type: Array, default: () => [] },
  writes: { type: Array, default: () => [] }
})

const FIELDS = [
  ['nationality', 'Passport'],
  ['current_location', 'Currently in'],
  ['budget_band', 'Budget'],
  ['travel_style', 'Pace'],
  ['climate_preference', 'Climate'],
  ['trip_start_date', 'Trip start'],
  ['trip_end_date', 'Trip end'],
  ['interests', 'Interests']
]
</script>

<template>
  <aside class="panel">
    <h3>What I remember</h3>
    <p class="muted small sub">Stored against your account, not this browser.</p>

    <dl v-if="profile">
      <template v-for="[key, label] in FIELDS" :key="key">
        <dt>{{ label }}</dt>
        <dd :class="{ unknown: !profile[key] }">{{ profile[key] || 'not set' }}</dd>
      </template>
      <template v-if="profile.visa_deadline_date">
        <dt>Deadline</dt>
        <dd class="deadline">
          {{ profile.visa_deadline_date }}
          <span v-if="profile.visa_deadline_note" class="muted"> - {{ profile.visa_deadline_note }}</span>
        </dd>
      </template>
    </dl>

    <div class="section">
      <h4>Visited this trip</h4>
      <ul v-if="visited.length" class="visited">
        <li v-for="(v, i) in visited" :key="i">
          <span class="country">{{ v.country }}</span>
          <span v-if="v.departure_date" class="muted small"> left {{ v.departure_date }}</span>
        </li>
      </ul>
      <p v-else class="muted small">Nothing logged yet.</p>
    </div>

    <div v-if="writes.length" class="section">
      <h4>Just remembered</h4>
      <ul class="writes">
        <li v-for="(w, i) in writes" :key="i">
          <span class="op mono">{{ w.operation }}</span>
          <span class="small">{{ Object.entries(w.payload).map(([k, v]) => `${k}=${v}`).join(', ') }}</span>
        </li>
      </ul>
    </div>

    <RouterLink class="edit small" to="/preferences">Edit my preferences →</RouterLink>
  </aside>
</template>

<style scoped>
aside { position: sticky; top: 20px; }
h3 { margin: 0 0 2px; font-size: 15px; }
.sub { margin: 0 0 14px; }

dl { display: grid; grid-template-columns: 88px 1fr; gap: 5px 10px; margin: 0; font-size: 13.5px; }
dt { color: var(--muted); }
dd { margin: 0; text-transform: capitalize; word-break: break-word; }
dd.unknown { color: #5d6472; font-style: italic; text-transform: none; }
dd.deadline { color: var(--warn); text-transform: none; }

.section { margin-top: 18px; border-top: 1px solid var(--line); padding-top: 14px; }
h4 { margin: 0 0 8px; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }

ul { margin: 0; padding: 0; list-style: none; }
.visited li { font-size: 13.5px; margin-bottom: 4px; }
.country { text-transform: capitalize; }

.writes li { display: flex; flex-direction: column; gap: 1px; margin-bottom: 8px; }
.op { font-size: 11px; color: var(--accent); }

.edit { display: inline-block; margin-top: 16px; color: var(--accent); text-decoration: none; }
</style>
