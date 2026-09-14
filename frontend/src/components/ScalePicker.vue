<script setup>
// A five-point scale as a row of buttons rather than a <select>.
//
// The dropdown it replaces hid the fact that these are ordered: you could not
// see that "budget" sits between "shoestring" and "mid" without opening it and
// reading top to bottom. As a row, the order IS the control, and the note under
// the selection explains the point you landed on - which is what makes five
// options answerable where five dropdown rows would just be five words.
//
// It stays one row at every width. A wrapping flex row broke the scale into
// "three then two" on a phone, which reads as two groups rather than one
// ordered spectrum and loses the only thing the control is for. Equal grid
// columns keep the order legible; the labels wrap instead.
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, required: true },
  label: { type: String, default: '' },
  hint: { type: String, default: '' },
  // Lets a second tap clear the field. Not every preference is one someone has.
  clearable: { type: Boolean, default: true }
})
const emit = defineEmits(['update:modelValue'])

const active = computed(() => props.options.find((o) => o.value === props.modelValue))

function pick(option) {
  emit('update:modelValue', props.clearable && option.value === props.modelValue ? '' : option.value)
}
</script>

<template>
  <div class="scale">
    <div v-if="label" class="head">
      <span class="label">{{ label }}</span>
      <span v-if="hint" class="muted small">{{ hint }}</span>
    </div>

    <div
      class="options"
      role="radiogroup"
      :aria-label="label"
      :style="{ '--n': options.length }"
    >
      <button
        v-for="option in options"
        :key="option.value"
        type="button"
        role="radio"
        :aria-checked="option.value === modelValue"
        class="option"
        :class="{ on: option.value === modelValue }"
        @click="pick(option)"
      >
        {{ option.label }}
      </button>
    </div>

    <p class="note muted small">
      <template v-if="active?.note">{{ active.note }}</template>
      <template v-else-if="active">{{ active.label }}</template>
      <template v-else>Not set — tap one. Tap it again to clear it.</template>
    </p>
  </div>
</template>

<style scoped>
.scale { margin-bottom: var(--sp-5); }

.head { display: flex; justify-content: space-between; align-items: baseline; gap: var(--sp-3); margin-bottom: 7px; }
.label { font-size: var(--fs-sm); color: var(--muted); }

.options { display: grid; grid-template-columns: repeat(var(--n, 5), 1fr); gap: 5px; }

.option {
  display: grid;
  place-items: center;
  min-height: 46px;
  padding: 7px 4px;
  font-size: 12.5px;
  line-height: 1.2;
  text-align: center;
  border-radius: var(--radius-sm);
  background: var(--bg);
  color: var(--muted);
  /* "Comfortable" does not fit one line at phone width. Hyphenating is the
     difference between "Comfort-able" and "Comfortab le". */
  hyphens: auto;
  overflow-wrap: break-word;
}
.option:hover:not(.on) { color: var(--text); border-color: var(--accent-dim); transform: none; }
.option.on {
  background: var(--accent-dim);
  border-color: var(--accent);
  color: var(--text);
  font-weight: 600;
  box-shadow: 0 0 0 1px var(--accent-soft);
}

@media (max-width: 420px) {
  .option { font-size: 11px; padding: 6px 2px; letter-spacing: -.01em; }
}

/* Reserved height, so picking an option with a one-line note does not shift
   the rest of the form up relative to one with a two-line note. */
.note { margin: 7px 0 0; min-height: 34px; }
</style>
