import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0B0F14',
        panel: '#121821',
        'panel-2': '#1A2230',
        line: '#253043',
        text: '#E6EDF3',
        muted: '#8B98A9',
        ok: '#22C55E',
        warn: '#F59E0B',
        crit: '#EF4444',
        accent: '#38BDF8',
        baseline: '#94A3B8',
        'chart-a': '#7C8BA1', // Store A line: separates from accent on panel (dataviz validator, ΔE 16)
        agent: {
          vision: '#A78BFA',
          rag: '#2DD4BF',
          demand: '#38BDF8',
          pricing: '#F59E0B',
          procurement: '#A3E635',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config
