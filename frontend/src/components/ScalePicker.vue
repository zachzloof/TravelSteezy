<script setup>
// A five-point scale as five buttons rather than a <select>.
//
// The dropdown it replaces hid the fact that these are ordered: you could not
// see that "budget" sits between "shoestring" and "mid" without opening it and
// reading top to bottom. As a row, the order IS the control, and the note under
// the selection explains the point you landed on - which is what makes five
// options answerable where five dropdown rows would just be five words.
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

    <div class="options" role="radiogroup" :aria-label="label">
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
.scale { margin-bottom: 18px; }

.head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; margin-bottom: 7px; }
.label { font-size: 13px; color: var(--muted); }

.options { display: flex; gap: 6px; flex-wrap: wrap; }

.option {
  flex: 1 1 0;
  min-width: 78px;
  padding: 9px 6px;
  font-size: 12.5px;
  line-height: 1.25;
  text-align: center;
  border-radius: 8px;
  background: var(--bg);
  color: var(--muted);
}
.option:hover:not(.on) { color: var(--text); border-color: var(--accent-dim); }
.option.on {
  background: var(--accent-dim);
  border-color: var(--accent);
  color: #e9fff4;
  font-weight: 600;
}

.note { margin: 7px 0 0; min-height: 18px; }
</style>
