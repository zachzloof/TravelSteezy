<script setup>
// One to five stars, used on every stop in the history panel.
//
// This is the highest-value single control in the app: a rating on somewhere
// they have been is what lets the assistant reason about somewhere they have
// not. A 2/5 on Hanoi is the reason Ho Chi Minh City gets ranked carefully.
// So it is one tap, editable forever, and clearable by re-tapping the same star.
import { ref } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: null },
  readonly: { type: Boolean, default: false },
  label: { type: String, default: 'Rating' }
})
const emit = defineEmits(['update:modelValue'])

const hovered = ref(0)

function set(value) {
  if (props.readonly) return
  emit('update:modelValue', value === props.modelValue ? null : value)
}
</script>

<template>
  <div class="stars" :class="{ readonly }" role="group" :aria-label="label">
    <button
      v-for="n in 5"
      :key="n"
      type="button"
      class="star"
      :class="{ on: n <= (hovered || modelValue || 0) }"
      :disabled="readonly"
      :aria-label="`${n} out of 5`"
      :title="readonly ? `${modelValue}/5` : `Rate ${n}/5`"
      @click="set(n)"
      @mouseenter="hovered = readonly ? 0 : n"
      @mouseleave="hovered = 0"
    >★</button>
    <span v-if="!modelValue && !readonly" class="muted small unrated">not rated</span>
  </div>
</template>

<style scoped>
.stars { display: inline-flex; align-items: center; gap: 1px; }

.star {
  border: none;
  background: none;
  padding: 0 1px;
  font-size: 15px;
  line-height: 1;
  color: var(--stone-700);
  transition: color .12s, transform .12s;
}
.star:hover:not(:disabled) { transform: scale(1.15); }
.star.on { color: var(--warn); }
.star:disabled { cursor: default; opacity: 1; }

.unrated { margin-left: 6px; }
.readonly .star { font-size: 13px; }
</style>
