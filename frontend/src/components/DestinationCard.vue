<script setup>
import Markdown from './Markdown.vue'

defineProps({ card: { type: Object, required: true } })
</script>

<template>
  <article class="card" :class="card.verdict">
    <header>
      <span class="rank" aria-hidden="true">{{ card.rank }}</span>
      <h4>{{ card.destination }}</h4>
      <span class="tag" :class="card.verdict">{{ card.verdict }}</span>
    </header>

    <p v-if="card.rationale" class="rationale"><Markdown :text="card.rationale" inline /></p>

    <div v-if="card.season_flag || card.visa_flag" class="flags">
      <div v-if="card.season_flag" class="flag season">
        <span class="flag-label">Season</span>{{ card.season_flag }}
      </div>
      <div v-if="card.visa_flag" class="flag visa">
        <span class="flag-label">Visa</span>{{ card.visa_flag }}
      </div>
    </div>

    <div class="cols">
      <div v-if="card.pros.length">
        <p class="eyebrow good">Pros</p>
        <ul><li v-for="(p, i) in card.pros" :key="i"><Markdown :text="p" inline /></li></ul>
      </div>
      <div v-if="card.cons.length">
        <p class="eyebrow bad">Cons</p>
        <ul><li v-for="(c, i) in card.cons" :key="i"><Markdown :text="c" inline /></li></ul>
      </div>
    </div>

    <div v-if="card.backpacker_notes && card.backpacker_notes.length" class="notes">
      <p class="eyebrow">Backpacker notes</p>
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
  /* Pros and cons go side by side when the CARD is wide enough, not when the
     window is. In a three-up grid on a desktop each card is only ~300px, so a
     viewport media query put two columns into a space that fits one. */
  container-type: inline-size;

  display: flex;
  flex-direction: column;
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-left: 3px solid var(--line);
  border-radius: var(--radius);
  padding: var(--sp-4);
  box-shadow: var(--shadow-sm);
  height: 100%;
  transition: transform var(--dur) var(--ease-out), box-shadow var(--dur) ease, border-color var(--dur) ease;
}
@media (hover: hover) {
  .card:hover { transform: translateY(-3px); }
  .card.go:hover { box-shadow: var(--glow-moss); border-color: var(--moss-dim); }
  .card.maybe:hover { box-shadow: 0 0 0 1px var(--warn-soft), 0 8px 24px -8px rgba(215, 162, 63, .35); border-color: var(--warn-dim); }
  .card.avoid:hover { box-shadow: 0 0 0 1px var(--bad-soft), 0 8px 24px -8px rgba(193, 87, 63, .35); border-color: var(--bad-dim); }
}
.card.go { border-left-color: var(--moss); }
.card.maybe { border-left-color: var(--warn); }
.card.avoid { border-left-color: var(--bad); }

header { display: flex; align-items: center; gap: var(--sp-2); margin-bottom: var(--sp-2); }
.rank {
  display: grid;
  place-items: center;
  flex: none;
  width: 21px;
  height: 21px;
  border-radius: var(--radius-xs);
  background: var(--bg);
  border: 1px solid var(--line);
  color: var(--muted);
  font-size: 11.5px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.card.go .rank { color: var(--moss-bright); border-color: var(--moss-dim); }
h4 { margin: 0; font-size: 15.5px; flex: 1; min-width: 0; text-transform: capitalize; }

.rationale { margin: 0 0 var(--sp-3); font-size: 14px; }

.flags { display: flex; flex-direction: column; gap: 6px; margin-bottom: var(--sp-3); }
.flag {
  font-size: var(--fs-sm);
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  line-height: 1.4;
}
.flag-label {
  display: inline-block;
  margin-right: 6px;
  font-size: var(--fs-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .05em;
  opacity: .8;
}
.flag.season { background: var(--warn-soft); border: 1px solid var(--warn-dim); color: #f0cb95; }
.flag.visa { background: var(--bad-soft); border: 1px solid var(--bad-dim); color: #f0b9b7; }

.cols { display: grid; grid-template-columns: 1fr; gap: var(--sp-3); }
@container (min-width: 360px) {
  .cols { grid-template-columns: 1fr 1fr; gap: var(--sp-4); }
}

.eyebrow.good { color: var(--moss-bright); }
.eyebrow.bad { color: #eeb4b2; }

ul { margin: 0; padding-left: 16px; font-size: 13.5px; }
li { margin-bottom: 3px; }
li:last-child { margin-bottom: 0; }

.notes {
  margin-top: var(--sp-3);
  border-top: 1px solid var(--line);
  padding-top: var(--sp-3);
}
.notes ul { font-size: 13.5px; }
.sources { margin: var(--sp-2) 0 0; font-size: var(--fs-xs); color: var(--muted-2); word-break: break-all; }

.cost { margin: var(--sp-3) 0 0; font-size: var(--fs-sm); color: var(--muted); }
</style>
