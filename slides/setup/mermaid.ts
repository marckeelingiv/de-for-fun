import { defineMermaidSetup } from '@slidev/types'

export default defineMermaidSetup(() => ({
  theme: 'base',
  securityLevel: 'loose',
  themeVariables: {
    background: '#070a12',
    mainBkg: '#111827',
    secondBkg: '#182235',
    primaryColor: '#111827',
    primaryBorderColor: '#00d4ff',
    primaryTextColor: '#e8f0ff',
    secondaryColor: '#182235',
    secondaryBorderColor: '#a855f7',
    tertiaryColor: '#0c1320',
    lineColor: '#7dd3fc',
    textColor: '#e8f0ff',
    clusterBkg: 'rgba(168, 85, 247, 0.12)',
    clusterBorder: '#a855f7',
    fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
  },
}))
