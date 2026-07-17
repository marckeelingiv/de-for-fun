<script setup lang="ts">
defineProps<{
  name: string
  model: string
  description: string
  accent?: 'primary' | 'secondary' | 'accent' | 'warning'
}>()
</script>

<template>
  <article class="metric-card" :data-accent="accent || 'primary'">
    <span>{{ model }}</span>
    <h3>{{ name }}</h3>
    <p>{{ description }}</p>
  </article>
</template>

<style scoped>
.metric-card {
  min-height: 128px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface-glass);
  padding: 0.9rem;
}

.metric-card[data-accent='primary'] { border-color: color-mix(in srgb, var(--primary), transparent 32%); }
.metric-card[data-accent='secondary'] { border-color: color-mix(in srgb, var(--secondary), transparent 32%); }
.metric-card[data-accent='accent'] { border-color: color-mix(in srgb, var(--accent), transparent 32%); }
.metric-card[data-accent='warning'] { border-color: color-mix(in srgb, var(--warning), transparent 32%); }

span {
  color: var(--deck-muted);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h3 {
  margin: 0.35rem 0;
  color: var(--deck-fg);
  font-family: var(--font-mono);
  font-size: 1.05rem;
}

p {
  margin: 0;
  font-size: 0.84rem;
  line-height: 1.35;
}
</style>
