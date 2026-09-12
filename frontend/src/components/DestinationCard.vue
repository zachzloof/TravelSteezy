<script setup>
import Markdown from './Markdown.vue'

defineProps({ card: { type: Object, required: true } })
</script>

<template>
  <article class="card" :class="card.verdict">
    <header>
      <span class="rank">#{{ card.rank }}</span>
      <h4>{{ card.destination }}</h4>
      <span class="tag" :class="card.verdict">{{ card.verdict }}</span>
    </header>

    <p v-if="card.rationale" class="rationale"><Markdown :text="card.rationale" inline /></p>

    <div v-if="card.season_flag" class="flag season">Season: {{ card.season_flag }}</div>
    <div v-if="card.visa_flag" class="flag visa">Visa: {{ card.visa_flag }}</div>

    <div class="cols">
      <div v-if="card.pros.length">
        <h5>Pros</h5>
        <ul><li v-for="(p, i) in card.pros" :key="i"><Markdown :text="p" inline /></li></ul>
      </div>
      <div v-if="card.cons.length">
        <h5>Cons</h5>
        <ul><li v-for="(c, i) in card.cons" :key="i"><Markdown :text="c" inline /></li></ul>
      </div>
    </div>

    <div v-if="card.backpacker_notes && card.backpacker_notes.length" class="notes">
      <h5>Backpacker notes</h5>
      <ul><li v-for="(n, i) in card.backpacker_notes" :key="i"><Markdown :text="n" inline /></li></ul>
      <p v-if="card.source_ids && card.source_ids.length" class="sources mono">
        sources: {{ card.source_ids.join(', ') }}
      </p>
    </div>

    <p v-if="card.est_cost_note" class="cost"><Markdown :text="card.est_cost_note" inline /></p>
  </article>
</template>

<style scoped>
.card {
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-left: 3px solid var(--line);
  border-radius: var(--radius);
  padding: 15px 17px;
  box-shadow: var(--shadow-sm);
  height: 100%;
  transition: transform var(--dur) var(--ease-out), box-shadow var(--dur) ease, border-color var(--dur) ease;
}
.card:hover { transform: translateY(-3px); }
.card.go { border-left-color: var(--moss); }
.card.go:hover { box-shadow: var(--glow-moss); border-color: var(--moss-dim); }
.card.maybe { border-left-color: var(--warn); }
.card.maybe:hover { box-shadow: 0 0 0 1px var(--warn-soft), 0 8px 24px -8px rgba(215, 162, 63, .35); border-color: var(--warn-dim); }
.card.avoid { border-left-color: var(--bad); }
.card.avoid:hover { box-shadow: 0 0 0 1px var(--bad-soft), 0 8px 24px -8px rgba(193, 87, 63, .35); border-color: var(--bad-dim); }

header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.rank { color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; }
h4 { margin: 0; font-size: 16px; flex: 1; text-transform: capitalize; }

.rationale { margin: 0 0 10px; font-size: 14px; }

.flag {
  font-size: 13px;
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
}
.flag.season { background: var(--warn-soft); border: 1px solid var(--warn-dim); color: #f0cb95; }
.flag.visa { background: var(--bad-soft); border: 1px solid var(--bad-dim); color: #f0b9b7; }

.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 6px; }
@media (max-width: 700px) { .cols { grid-template-columns: 1fr; } }

h5 {
  margin: 0 0 5px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--muted);
}
ul { margin: 0; padding-left: 17px; font-size: 13.5px; }
li { margin-bottom: 3px; }

.notes {
  margin-top: 12px;
  border-top: 1px solid var(--line);
  padding-top: 10px;
}
.notes ul { font-size: 13.5px; }
.sources { margin: 8px 0 0; font-size: 11px; color: var(--muted-2); }

.cost { margin: 12px 0 0; font-size: 13px; color: var(--muted); }
</style>
