<script setup>
// One to five stars, used on every stop in the history panel.
//
// This is the highest-value single control in the app: a rating on somewhere
// they have been is what lets the assistant reason about somewhere they have
// not. A 2/5 on Hanoi is the reason Ho Chi Minh City gets ranked carefully.
// So it is one tap, editable forever, and clearable by re-tapping the same star.
//
// `size` exists so the review prompt can use the same component at a size you
// can actually hit with a thumb. It used to hand-roll its own row of stars,
// which is how the two ended up with different clear-on-retap behaviour.
import { ref } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: null },
  readonly: { type: Boolean, default: false },
  label: { type: String, default: 'Rating' },
  size: { type: String, default: 'sm' },
  // The "not rated" hint is useful in a list of stops, and redundant next to a
  // prompt that already asks the question.
  showHint: { type: Boolean, default: true }
})
const emit = defineEmits(['update:modelValue'])

const hovered = ref(0)

function set(value) {
  if (props.readonly) return
  emit('update:modelValue', value === props.modelValue ? null : value)
}
</script>

<template>
  <div class="stars" :class="[size, { readonly }]" role="group" :aria-label="label">
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
    <span v-if="modelValue && size === 'lg'" class="muted small note">{{ modelValue }}/5</span>
    <span v-else-if="!modelValue && !readonly && showHint" class="muted small note">not rated</span>
  </div>
</template>

<style scoped>
.stars { display: inline-flex; align-items: center; }

.star {
  border: none;
  background: none;
  padding: 0 1px;
  font-size: 15px;
  line-height: 1;
  color: var(--stone-700);
  border-radius: var(--radius-xs);
  transition: color .12s, transform .12s ease, filter .12s ease;
}
.star:hover:not(:disabled) { transform: scale(1.18); background: none; }
.star.on { color: var(--warn); filter: drop-shadow(0 0 4px rgba(215, 162, 63, .45)); }
.star:disabled { cursor: default; opacity: 1; }

.note { margin-left: var(--sp-2); }

/* Large: the primary control on the review prompt. */
.lg .star { font-size: 27px; padding: 0 3px; }
.readonly .star { font-size: 13px; }

/* An editable row of stars has to be hittable without aiming. */
@media (pointer: coarse) {
  .stars:not(.readonly) .star { font-size: 20px; padding: 6px 5px; }
  .stars.lg:not(.readonly) .star { font-size: 30px; padding: 6px; }
}
</style>
