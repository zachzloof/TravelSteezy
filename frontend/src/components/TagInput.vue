<script setup>
// A chip list you add to by typing and pressing Enter. Used for passports and
// interests - both are genuinely lists, and both were previously a single
// comma-separated text box that quietly made "United Kingdom, Ireland" look
// like one very oddly named country.
import { ref } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  label: { type: String, default: '' },
  hint: { type: String, default: '' },
  placeholder: { type: String, default: 'Type and press Enter' },
  suggestions: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:modelValue'])

const draft = ref('')

function add(value) {
  const text = String(value ?? draft.value).trim()
  draft.value = ''
  if (!text) return
  const lower = text.toLowerCase()
  if (props.modelValue.some((v) => String(v).toLowerCase() === lower)) return
  emit('update:modelValue', [...props.modelValue, text])
}

function remove(index) {
  emit('update:modelValue', props.modelValue.filter((_, i) => i !== index))
}

// Backspace on an empty box removes the last chip - the behaviour everyone
// already expects from every other tag field they have ever used.
function backspace() {
  if (!draft.value && props.modelValue.length) remove(props.modelValue.length - 1)
}

function unused(suggestion) {
  return !props.modelValue.some((v) => String(v).toLowerCase() === suggestion.toLowerCase())
}
</script>

<template>
  <div class="tags">
    <div v-if="label" class="head">
      <span class="label">{{ label }}</span>
      <span v-if="hint" class="muted small">{{ hint }}</span>
    </div>

    <div class="box">
      <TransitionGroup name="pop">
        <span v-for="(value, index) in modelValue" :key="value" class="chip">
          <span class="text">{{ value }}</span>
          <button type="button" class="x" :aria-label="`Remove ${value}`" @click="remove(index)">×</button>
        </span>
      </TransitionGroup>
      <input
        v-model="draft"
        :placeholder="modelValue.length ? 'Add another…' : placeholder"
        :aria-label="label || 'Add an entry'"
        @keydown.enter.prevent="add()"
        @keydown.delete="backspace"
        @blur="add()"
      />
    </div>

    <div v-if="suggestions.filter(unused).length" class="suggestions">
      <button
        v-for="s in suggestions.filter(unused)"
        :key="s"
        type="button"
        class="ghost suggestion"
        @click="add(s)"
      >+ {{ s }}</button>
    </div>
  </div>
</template>

<style scoped>
.tags { margin-bottom: var(--sp-5); }

.head { display: flex; justify-content: space-between; align-items: baseline; gap: var(--sp-3); margin-bottom: 7px; }
.label { font-size: var(--fs-sm); color: var(--muted); }

.box {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  padding: 7px 8px;
  min-height: 46px;
  transition: border-color var(--dur-fast) ease, box-shadow var(--dur) ease;
}
.box:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }

.chip {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: var(--radius-pill);
  padding: 3px 4px 3px 11px;
  font-size: var(--fs-sm);
  max-width: 100%;
  transition: border-color var(--dur-fast) ease;
}
.chip:hover { border-color: var(--accent-dim); }
.chip .text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.x {
  display: grid;
  place-items: center;
  flex: none;
  width: 22px; height: 22px;
  border: none; background: none; color: var(--muted);
  padding: 0; font-size: 16px; line-height: 1;
  border-radius: 50%;
}
.x:hover { color: var(--bad-bright); background: var(--bad-soft); transform: none; }
@media (pointer: coarse) { .x { width: 26px; height: 26px; } }

input {
  flex: 1;
  min-width: 110px;
  width: auto;
  border: none;
  background: none;
  padding: 4px 2px;
}
input:focus { outline: none; border: none; box-shadow: none; background: none; }

.suggestions { display: flex; flex-wrap: wrap; gap: 5px; margin-top: var(--sp-2); }
.suggestion {
  padding: 5px 11px;
  font-size: 12px;
  border-radius: var(--radius-pill);
  border-color: var(--line);
  color: var(--muted);
}
.suggestion:hover:not(:disabled) { color: var(--accent-bright); border-color: var(--accent-dim); background: var(--accent-soft); }
</style>
