<script setup>
// Renders LLM output as actual markdown instead of a wall of literal
// "**bold**" and "- " asterisks in the chat bubble.
//
// The assistant's replies (and the destination cards' rationale/pros/cons/
// backpacker notes) are prompted for and produced as prose that includes real
// markdown - bold, bullet lists, the odd link. Rendering it with `{{ m.text }}`
// showed that markup completely literally, which is the bug this fixes.
//
// Sanitized with DOMPurify because this is `v-html`: the text ultimately comes
// from an LLM, and the RAG corpus it draws on could in principle carry HTML- or
// script-looking content. Only a plain-prose tag allowlist gets through.
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  text: { type: String, default: '' },
  // Compact mode for list items / short fields (card rationale, a pro/con line):
  // renders without the wrapping <p>, so it doesn't add paragraph spacing
  // inside a <li> or a one-line field.
  inline: { type: Boolean, default: false }
})

marked.setOptions({ gfm: true, breaks: true })

// Links open in a new tab without handing the new page a `window.opener`.
const renderer = new marked.Renderer()
const originalLink = renderer.link.bind(renderer)
renderer.link = (...args) => originalLink(...args).replace('<a ', '<a target="_blank" rel="noopener noreferrer" ')

const ALLOWED_TAGS = [
  'p', 'br', 'strong', 'em', 'code', 'pre', 'a', 'ul', 'ol', 'li',
  'blockquote', 'h1', 'h2', 'h3', 'h4', 'hr', 'del', 'table', 'thead',
  'tbody', 'tr', 'th', 'td'
]

const html = computed(() => {
  const raw = props.inline
    ? marked.parseInline(props.text || '', { renderer })
    : marked.parse(props.text || '', { renderer })
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS,
    ALLOWED_ATTR: ['href', 'target', 'rel']
  })
})
</script>

<template>
  <div class="md" :class="{ inline }" v-html="html" />
</template>

<style scoped>
.md { word-break: break-word; }
.md.inline { display: inline; }

.md :deep(p) { margin: 0 0 10px; }
.md :deep(p:last-child) { margin-bottom: 0; }
.md.inline :deep(p) { display: inline; margin: 0; }

.md :deep(ul), .md :deep(ol) { margin: 4px 0 10px; padding-left: 20px; }
.md :deep(li) { margin-bottom: 3px; }
.md :deep(li:last-child) { margin-bottom: 0; }

.md :deep(strong) { font-weight: 650; }
.md :deep(a) { color: var(--accent); }

.md :deep(code) {
  background: var(--bg);
  padding: 1px 5px;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: .92em;
}
.md :deep(pre) {
  background: var(--bg);
  border: 1px solid var(--line);
  padding: 10px 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0 0 10px;
}
.md :deep(pre) code { background: none; padding: 0; }

.md :deep(blockquote) {
  border-left: 2px solid var(--line);
  margin: 6px 0 10px;
  padding-left: 10px;
  color: var(--muted);
}

.md :deep(h1), .md :deep(h2), .md :deep(h3), .md :deep(h4) {
  font-size: 1em;
  font-weight: 650;
  margin: 10px 0 4px;
}
.md :deep(h1:first-child), .md :deep(h2:first-child),
.md :deep(h3:first-child), .md :deep(h4:first-child) { margin-top: 0; }

.md :deep(hr) { border: none; border-top: 1px solid var(--line); margin: 10px 0; }

.md :deep(table) { border-collapse: collapse; margin: 0 0 10px; font-size: .95em; }
.md :deep(th), .md :deep(td) { border: 1px solid var(--line); padding: 4px 8px; text-align: left; }
</style>
