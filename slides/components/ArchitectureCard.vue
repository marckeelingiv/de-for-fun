<script setup lang="ts">
defineProps<{
  title: string
  detail: string
  tag: string
}>()
</script>

<template>
  <article class="architecture-card">
    <div class="orb" />
    <span>{{ tag }}</span>
    <h3>{{ title }}</h3>
    <p>{{ detail }}</p>
  </article>
</template>

<style scoped>
.architecture-card {
  position: relative;
  min-height: 150px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: linear-gradient(150deg, var(--surface-raised), var(--surface-muted));
  padding: 1rem;
}

.orb {
  position: absolute;
  right: -32px;
  top: -38px;
  width: 112px;
  height: 112px;
  border-radius: 999px;
  background: radial-gradient(circle, var(--primary), transparent 68%);
  opacity: 0.28;
}

span {
  color: var(--primary);
  font-family: var(--font-mono);
  font-size: 0.74rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h3 {
  margin: 0.55rem 0 0.3rem;
  color: var(--deck-fg);
  font-size: 1.35rem;
}

p {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.4;
}
</style>
