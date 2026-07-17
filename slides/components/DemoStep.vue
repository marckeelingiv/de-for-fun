<script setup lang="ts">
defineProps<{
  title: string
  outcome: string
  risk?: string
}>()
</script>

<template>
  <article class="demo-step">
    <div class="demo-marker">LIVE DEMO</div>
    <h3>{{ title }}</h3>
    <p>{{ outcome }}</p>
    <p v-if="risk" class="risk">Fallback: {{ risk }}</p>
    <slot />
  </article>
</template>

<style scoped>
.demo-step {
  border: 1px solid color-mix(in srgb, var(--accent), transparent 35%);
  border-radius: var(--radius-xl);
  background: linear-gradient(140deg, rgba(29, 209, 161, 0.12), var(--surface-glass));
  box-shadow: var(--shadow-soft);
  padding: 1.1rem;
}

h3 {
  margin: 0.8rem 0 0.25rem;
  color: var(--deck-fg);
  font-size: 1.8rem;
}

p {
  margin: 0 0 0.8rem;
  line-height: 1.38;
}

.risk {
  border-left: 3px solid var(--warning);
  border-radius: var(--radius-sm);
  background: rgba(254, 202, 87, 0.08);
  padding: 0.6rem 0.75rem;
  color: var(--deck-fg);
  font-size: 0.92rem;
}
</style>
