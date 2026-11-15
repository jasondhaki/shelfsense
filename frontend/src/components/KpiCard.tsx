import { useEffect, useRef, useState } from 'react'
import { prefersReducedMotion } from '../lib/format'

const COUNT_MS = 300

function useCountUp(target: number): number {
  const [shown, setShown] = useState(target)
  const from = useRef(target)
  const reduced = prefersReducedMotion()

  useEffect(() => {
    if (reduced) {
      from.current = target
      return
    }
    const start = performance.now()
    const origin = from.current
    let frame = 0
    const tick = (now: number) => {
      const p = Math.min((now - start) / COUNT_MS, 1)
      setShown(origin + (target - origin) * p)
      if (p < 1) frame = requestAnimationFrame(tick)
      else from.current = target
    }
    frame = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(frame)
      from.current = target
    }
  }, [target, reduced])

  return reduced ? target : shown
}

interface Props {
  label: string
  value: number | null
  format: (n: number) => string
  sub?: string
  /** When set, the card turns ok-green at or above this value and shows the target. */
  target?: number
}

export default function KpiCard({ label, value, format, sub, target }: Props) {
  const shown = useCountUp(value ?? 0)
  const met = target !== undefined && value !== null && value >= target

  return (
    <div className="min-w-[156px] rounded-md border border-line bg-panel-2 px-3 py-2">
      <div className="text-[11px] text-muted">{label}</div>
      <div
        className={`font-mono text-xl font-semibold tabular-nums ${met ? 'text-ok' : 'text-text'}`}
      >
        {value === null ? '—' : format(shown)}
      </div>
      <div className="text-[11px] tabular-nums text-muted">
        {target !== undefined ? `target ≥ ${target}%${met ? ' · met' : ''}` : sub}
      </div>
    </div>
  )
}
