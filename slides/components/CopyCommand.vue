<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  command: string
  label?: string
  note?: string
}>()

const copied = ref(false)

const lines = computed(() => props.command.trim().split('\n'))

async function copyCommand() {
  await navigator.clipboard.writeText(props.command.trim())
  copied.value = true
  window.setTimeout(() => {
    copied.value = false
  }, 1400)
}
</script>

<template>
  <section class="copy-command">
    <header>
      <span>{{ label || 'Terminal' }}</span>
      <button type="button" @click="copyCommand">{{ copied ? 'Copied' : 'Copy' }}</button>
    </header>
    <pre><code><span v-for="(line, index) in lines" :key="index"><span class="prompt">$</span> {{ line }}<br /></span></code></pre>
    <p v-if="note" class="note">{{ note }}</p>
  </section>
</template>

<style scoped>
.copy-command {
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, color-mix(in srgb, var(--code-bg), var(--primary) 4%), var(--code-bg));
  box-shadow: var(--shadow-soft);
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  padding: 0.65rem 0.8rem;
  color: var(--deck-muted);
  font-family: var(--font-mono);
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

button {
  border: 1px solid color-mix(in srgb, var(--primary), transparent 28%);
  border-radius: 999px;
  background: rgba(0, 212, 255, 0.1);
  color: var(--primary);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 0.76rem;
  padding: 0.25rem 0.62rem;
}

button:hover {
  background: rgba(0, 212, 255, 0.2);
}

pre {
  margin: 0;
  padding: 0.9rem 1rem 1rem;
  color: var(--code-fg);
  font-family: var(--font-mono);
  font-size: 0.95rem;
  line-height: 1.65;
  white-space: pre-wrap;
}

.prompt {
  color: var(--code-prompt);
}

.note {
  border-top: 1px solid var(--border);
  margin: 0;
  padding: 0.65rem 0.8rem;
  color: var(--deck-muted);
  font-size: 0.82rem;
}
</style>
