import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Light "fresh market" theme (frontend.jpg). Text tokens meet 4.5:1 on panel and bg.
        bg: '#EEF3F0',
        panel: '#FFFFFF',
        'panel-2': '#F4F7F5',
        line: '#DDE6E1',
        text: '#0F2A1F',
        muted: '#56675E',
        ok: '#15803D',
        warn: '#B45309',
        crit: '#B91C1C',
        accent: '#0F7B57',
        baseline: '#8796A6',
        'chart-a': '#8796A6',
        mint: '#DCF5E8',
        forest: {
          950: '#06261C',
          900: '#0A3327',
          800: '#0E4232',
          700: '#155A43',
          600: '#1E7556',
        },
        agent: {
          vision: '#7C3AED',
          rag: '#0F766E',
          demand: '#0369A1',
          pricing: '#B45309',
          procurement: '#4D7C0F',
        },
      },
      fontFamily: {
        sans: ['Manrope', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(15, 42, 31, 0.04), 0 8px 24px -12px rgba(15, 42, 31, 0.12)',
      },
    },
  },
  plugins: [],
} satisfies Config
