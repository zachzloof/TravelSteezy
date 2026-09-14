<script setup>
// A bottom sheet, for content that is a sidebar on a desktop and has nowhere
// to go on a phone.
//
// The alternative — stacking the sidebar underneath the chat — meant scrolling
// past an entire screen of conversation to find out what the assistant
// remembers about you, which in practice meant nobody ever saw it. A sheet
// keeps it one tap away without taking any space from the thing you came for.
//
// Teleported to <body> so it cannot be clipped or repositioned by a scrolling
// ancestor, and it locks the page behind it so the background does not scroll
// under your finger while the sheet is open.
import { onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' }
})
const emit = defineEmits(['close'])

function onKeydown(event) {
  if (event.key === 'Escape') emit('close')
}

function lock(on) {
  document.body.style.overflow = on ? 'hidden' : ''
  if (on) window.addEventListener('keydown', onKeydown)
  else window.removeEventListener('keydown', onKeydown)
}

watch(() => props.open, lock)

// A route change can unmount this while it is still open; the page must not be
// left permanently unscrollable if that happens.
onBeforeUnmount(() => lock(false))
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="open" class="sheet-root" role="dialog" aria-modal="true" :aria-label="title">
        <div class="scrim" @click="emit('close')" />

        <div class="sheet">
          <div class="grip" aria-hidden="true" />
          <header class="head">
            <h2>{{ title }}</h2>
            <button class="icon-btn" aria-label="Close" @click="emit('close')">×</button>
          </header>
          <div class="body">
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.sheet-root { position: fixed; inset: 0; z-index: 60; display: flex; align-items: flex-end; }

.scrim { position: absolute; inset: 0; background: rgba(0, 0, 0, .55); backdrop-filter: blur(3px); }

.sheet {
  position: relative;
  width: 100%;
  max-height: 86dvh;
  display: flex;
  flex-direction: column;
  background: var(--panel);
  border-top: 1px solid var(--line);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  box-shadow: var(--shadow-sheet);
  padding-bottom: var(--safe-b);
}

.grip {
  width: 38px;
  height: 4px;
  border-radius: var(--radius-pill);
  background: var(--stone-600);
  margin: 10px auto 2px;
  flex: none;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-2) var(--sp-4) var(--sp-3);
  border-bottom: 1px solid var(--line);
  flex: none;
}
.head h2 { margin: 0; font-size: var(--fs-h3); }

.body {
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: var(--sp-4) max(var(--sp-4), var(--safe-l)) var(--sp-5) max(var(--sp-4), var(--safe-r));
  /* Overscroll inside the sheet must not chain to the page behind it. */
  overscroll-behavior: contain;
}

.sheet-enter-active .sheet, .sheet-leave-active .sheet { transition: transform var(--dur) var(--ease-out); }
.sheet-enter-active .scrim, .sheet-leave-active .scrim { transition: opacity var(--dur) ease; }
.sheet-enter-from .sheet, .sheet-leave-to .sheet { transform: translateY(100%); }
.sheet-enter-from .scrim, .sheet-leave-to .scrim { opacity: 0; }
</style>
