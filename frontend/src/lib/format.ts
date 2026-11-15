export const CYCLE_TICKS = 168

export const usd = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })

export const simClock = (tick: number) => {
  const t = Math.min(tick, CYCLE_TICKS - 1)
  return `D${Math.floor(t / 24) + 1} ${String(t % 24).padStart(2, '0')}:00`
}

export const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
