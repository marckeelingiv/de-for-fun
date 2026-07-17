<script setup lang="ts">
import mermaid from 'mermaid'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { diagrams } from '../diagrams'

const props = defineProps<{
  chart?: string
  name?: string
}>()

const svg = ref('')
const id = `mermaid-${Math.random().toString(36).slice(2)}`

const cleanChart = computed(() => (props.chart || diagrams[props.name || ''] || '').trim())

function cssToken(name: string, fallback: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

async function renderDiagram() {
  if (!cleanChart.value) {
    svg.value = ''
    return
  }
  await nextTick()
  mermaid.initialize({
    startOnLoad: false,
    theme: 'base',
    securityLevel: 'loose',
    themeVariables: {
      background: cssToken('--deck-bg', '#070a12'),
      mainBkg: cssToken('--diagram-node-bg', '#111827'),
      secondBkg: cssToken('--diagram-node-alt-bg', '#182235'),
      primaryColor: cssToken('--diagram-node-bg', '#111827'),
      primaryBorderColor: cssToken('--diagram-node-border', '#00d4ff'),
      primaryTextColor: cssToken('--diagram-text', '#e8f0ff'),
      secondaryColor: cssToken('--diagram-node-alt-bg', '#182235'),
      secondaryBorderColor: cssToken('--secondary', '#a855f7'),
      tertiaryColor: cssToken('--surface-muted', '#0c1320'),
      lineColor: cssToken('--diagram-edge', '#7dd3fc'),
      textColor: cssToken('--diagram-text', '#e8f0ff'),
      clusterBkg: cssToken('--diagram-cluster-bg', 'rgba(168, 85, 247, 0.12)'),
      clusterBorder: cssToken('--secondary', '#a855f7'),
      fontFamily: cssToken('--font-display', 'Inter, sans-serif'),
    },
  })
  const rendered = await mermaid.render(id, cleanChart.value)
  svg.value = rendered.svg
}

onMounted(renderDiagram)
watch(cleanChart, renderDiagram)
</script>

<template>
  <div class="mermaid-shell" v-html="svg" />
</template>

<style scoped>
.mermaid-shell {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 360px;
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  background: var(--surface-glass);
  box-shadow: var(--shadow-soft);
  padding: 1rem;
}

.mermaid-shell :deep(svg) {
  max-width: 100%;
  height: auto;
}
</style>
