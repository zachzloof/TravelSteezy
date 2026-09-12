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

    <div v-if="suggestions.length" class="suggestions">
      <button
        v-for="s in suggestions.filter((s) => !modelValue.some((v) => String(v).toLowerCase() === s.toLowerCase()))"
        :key="s"
        type="button"
        class="ghost small suggestion"
        @click="add(s)"
      >+ {{ s }}</button>
    </div>
  </div>
</template>

<style scoped>
.tags { margin-bottom: 18px; }

.head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; margin-bottom: 7px; }
.label { font-size: 13px; color: var(--muted); }

.box {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 7px 8px;
}
.box:focus-within { border-color: var(--accent-dim); box-shadow: 0 0 0 3px var(--accent-soft); }

.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 2px 4px 2px 10px;
  font-size: 13px;
  transition: transform var(--dur) var(--ease-spring), border-color var(--dur-fast) ease;
}
.chip:hover { border-color: var(--accent-dim); transform: translateY(-1px); }
.x {
  border: none; background: none; color: var(--muted);
  padding: 0 5px; font-size: 15px; line-height: 1;
}
.x:hover { color: var(--bad); }

input {
  flex: 1;
  min-width: 120px;
  width: auto;
  border: none;
  background: none;
  padding: 3px 2px;
}
input:focus { outline: none; border: none; }

.suggestions { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 7px; }
.suggestion { padding: 3px 9px; font-size: 12px; border-radius: 999px; }
</style>
