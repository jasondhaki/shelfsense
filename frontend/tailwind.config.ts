import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Tokens live in src/index.css (:root = light, .dark = dark) so one class name serves both themes.
        bg: 'rgb(var(--c-bg) / <alpha-value>)',
        panel: 'rgb(var(--c-panel) / <alpha-value>)',
        'panel-2': 'rgb(var(--c-panel-2) / <alpha-value>)',
        line: 'rgb(var(--c-line) / <alpha-value>)',
        text: 'rgb(var(--c-text) / <alpha-value>)',
        muted: 'rgb(var(--c-muted) / <alpha-value>)',
        ok: 'rgb(var(--c-ok) / <alpha-value>)',
        warn: 'rgb(var(--c-warn) / <alpha-value>)',
        crit: 'rgb(var(--c-crit) / <alpha-value>)',
        accent: 'rgb(var(--c-accent) / <alpha-value>)',
        baseline: 'rgb(var(--c-baseline) / <alpha-value>)',
        'chart-a': 'rgb(var(--c-chart-a) / <alpha-value>)',
        mint: 'rgb(var(--c-mint) / <alpha-value>)',
        forest: {
          950: 'rgb(var(--c-forest-950) / <alpha-value>)',
          900: 'rgb(var(--c-forest-900) / <alpha-value>)',
          800: 'rgb(var(--c-forest-800) / <alpha-value>)',
          700: 'rgb(var(--c-forest-700) / <alpha-value>)',
          600: 'rgb(var(--c-forest-600) / <alpha-value>)',
        },
        agent: {
          vision: 'rgb(var(--c-agent-vision) / <alpha-value>)',
          rag: 'rgb(var(--c-agent-rag) / <alpha-value>)',
          demand: 'rgb(var(--c-agent-demand) / <alpha-value>)',
          pricing: 'rgb(var(--c-agent-pricing) / <alpha-value>)',
          procurement: 'rgb(var(--c-agent-procurement) / <alpha-value>)',
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
