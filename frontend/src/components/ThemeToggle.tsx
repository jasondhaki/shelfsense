import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../lib/theme'

export default function ThemeToggle({ className = 'grid h-11 w-11 place-items-center rounded-full text-text hover:bg-panel' }: { className?: string }) {
  const theme = useTheme((s) => s.theme)
  const toggle = useTheme((s) => s.toggle)
  const dark = theme === 'dark'
  return (
    <button type="button" className={className} onClick={toggle} aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'} title={dark ? 'Light theme' : 'Dark theme'}>
      {dark ? <Sun size={22} aria-hidden strokeWidth={1.8} /> : <Moon size={22} strokeWidth={1.8} aria-hidden />}
    </button>
  )
}
