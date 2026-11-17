import { create } from 'zustand'

export type Theme = 'light' | 'dark'
const KEY = 'shelfsense.theme'

function initial(): Theme {
  try {
    const t = localStorage.getItem(KEY)
    if (t === 'light' || t === 'dark') return t
  } catch {
    // storage blocked: fall back to the OS preference
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

const apply = (t: Theme) => document.documentElement.classList.toggle('dark', t === 'dark')

/** Light/dark choice: remembered per browser, defaults to the OS setting. */
export const useTheme = create<{ theme: Theme; toggle: () => void }>((set, get) => ({
  theme: initial(),
  toggle: () => {
    const theme: Theme = get().theme === 'dark' ? 'light' : 'dark'
    try {
      localStorage.setItem(KEY, theme)
    } catch {
      // not remembered, still applied
    }
    apply(theme)
    set({ theme })
  },
}))

apply(useTheme.getState().theme)
