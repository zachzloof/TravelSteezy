<script setup>
// A segmented control for splitting a long page into sections.
//
// Both the Trip page and the Memory page were single scrolls of five or six
// full-width panels. That is survivable on a desktop and miserable on a phone,
// where finding the wishlist meant scrolling past the entire profile form and
// the whole route. Tabs turn "scroll and hope" into "pick the one you want".
//
// The strip scrolls horizontally when the labels do not fit, and the selected
// tab is scrolled into view, so a tab is never stranded off-screen.
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  // { id, label, count? } — count renders as a badge, and is hidden when zero
  // so an empty section does not advertise a "0".
  tabs: { type: Array, required: true },
  modelValue: { type: String, required: true },
  label: { type: String, default: 'Sections' }
})
const emit = defineEmits(['update:modelValue'])

const strip = ref(null)

watch(() => props.modelValue, async (id) => {
  await nextTick()
  strip.value?.querySelector(`[data-tab="${id}"]`)?.scrollIntoView({
    behavior: 'smooth', block: 'nearest', inline: 'nearest'
  })
})
</script>

<template>
  <div ref="strip" class="seg" role="tablist" :aria-label="label">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      :data-tab="tab.id"
      type="button"
      role="tab"
      :aria-selected="tab.id === modelValue"
      class="seg-btn"
      :class="{ on: tab.id === modelValue }"
      @click="emit('update:modelValue', tab.id)"
    >
      {{ tab.label }}
      <span v-if="tab.count" class="count">{{ tab.count }}</span>
    </button>
  </div>
</template>

<style scoped>
.seg {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-pill);
  overflow-x: auto;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
}
.seg::-webkit-scrollbar { display: none; }

.seg-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex: 1 0 auto;
  justify-content: center;
  white-space: nowrap;
  padding: 9px 16px;
  font-size: 13.5px;
  font-weight: 600;
  border: none;
  background: transparent;
  color: var(--muted);
  border-radius: var(--radius-pill);
}
.seg-btn:hover:not(.on) { color: var(--text); background: var(--panel-2); transform: none; }
.seg-btn.on {
  background: var(--accent-grad);
  color: var(--on-accent);
  box-shadow: var(--glow-accent);
}

.count {
  display: inline-grid;
  place-items: center;
  min-width: 19px;
  height: 19px;
  padding: 0 5px;
  border-radius: var(--radius-pill);
  background: var(--panel-2);
  color: var(--muted);
  font-size: var(--fs-xs);
  font-variant-numeric: tabular-nums;
}
.seg-btn.on .count { background: rgba(32, 18, 3, .22); color: var(--on-accent); }

@media (max-width: 560px) {
  .seg-btn { padding: 9px 13px; font-size: 13px; }
}
</style>
