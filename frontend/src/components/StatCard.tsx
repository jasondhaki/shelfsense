import { ArrowDownRight, ArrowUpRight, type LucideIcon } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
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

/** Area sparkline of the hourly history; decorative (the number beside it is the value). */
function Sparkline({ data, color }: { data: number[]; color: string }) {
  const id = useId()
  if (data.length < 2) return null
  const step = Math.max(1, Math.floor(data.length / 60)) // ≤ 60 points
  const pts = data.filter((_, i) => i % step === 0 || i === data.length - 1)
  const min = Math.min(...pts, 0)
  const max = Math.max(...pts)
  const span = max - min || 1
  const W = 200
  const H = 48
  const xy = pts.map((v, i) => [(i / (pts.length - 1)) * W, H - 4 - ((v - min) / span) * (H - 10)])
  const line = xy.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join('')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="absolute inset-x-0 bottom-0 h-12 w-full" aria-hidden>
      <defs>
        <linearGradient id={id} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.28" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${line}L${W},${H}L0,${H}Z`} fill={`url(#${id})`} />
      <path d={line} fill="none" stroke={color} strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

interface Props {
  label: string
  value: number | null
  format: (n: number) => string
  /** Change over the last 24 simulated hours, already formatted with its unit. */
  change: { value: number; text: string } | null
  history: number[]
  Icon: LucideIcon
  /** Tailwind classes for the icon tile, and the sparkline colour. */
  tile: string
  color: string
  hint: string
}

export default function StatCard({ label, value, format, change, history, Icon, tile, color, hint }: Props) {
  const shown = useCountUp(value ?? 0)
  const up = change && change.value >= 0
  const moved = change && Math.abs(change.value) >= 0.05
  return (
    <article className="zone relative overflow-hidden p-4 pb-12" title={hint}>
      <div className="flex items-center gap-3">
        <span className={`grid h-12 w-12 shrink-0 place-items-center rounded-full ${tile}`}>
          <Icon size={24} aria-hidden />
        </span>
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-muted">{label}</h3>
          <div className="flex flex-wrap items-baseline gap-x-2">
            <span className="text-2xl font-extrabold tracking-tight">{value === null ? '—' : format(shown)}</span>
            {moved && change && (
              <span
                className={`inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[11px] font-bold ${up ? 'bg-mint text-accent' : 'bg-crit/10 text-crit'}`}
                title="Change over the last 24 simulated hours"
              >
                {up ? <ArrowUpRight size={12} aria-hidden /> : <ArrowDownRight size={12} aria-hidden />}
                {change.text}
                <span className="font-semibold opacity-70">/ 24 h</span>
              </span>
            )}
          </div>
        </div>
      </div>
      <Sparkline data={history} color={color} />
    </article>
  )
}
