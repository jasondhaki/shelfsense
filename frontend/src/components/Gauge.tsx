/** 270° progress arc for waste reduction, with the 30% target marked on the track. */
export default function Gauge({ value, target }: { value: number | null; target: number }) {
  const R = 52
  const C = 2 * Math.PI * R
  const ARC = 0.75 // 270° of the circle
  const v = Math.min(Math.max(value ?? 0, 0), 100) / 100
  const met = value !== null && value >= target
  // target tick position, measured from the arc's start (135°, bottom-left)
  const a = ((135 + (target / 100) * 270) * Math.PI) / 180
  const tx = 60 + Math.cos(a) * R
  const ty = 60 + Math.sin(a) * R
  return (
    <div className="relative mx-auto w-40" role="meter" aria-label="Waste reduction" aria-valuemin={0} aria-valuemax={100} aria-valuenow={value ?? 0}>
      <svg viewBox="0 0 120 120" className="w-full -rotate-0" aria-hidden>
        <circle
          cx="60"
          cy="60"
          r={R}
          fill="none"
          stroke="rgb(var(--c-line))"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${C * ARC} ${C}`}
          transform="rotate(135 60 60)"
        />
        <circle
          cx="60"
          cy="60"
          r={R}
          fill="none"
          stroke="rgb(var(--c-forest-800))"
          className="transition-[stroke-dasharray] duration-500 dark:!stroke-accent"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${C * ARC * v} ${C}`}
          transform="rotate(135 60 60)"
        />
        <circle cx={tx} cy={ty} r="3.5" fill="rgb(var(--c-panel))" stroke="rgb(var(--c-warn))" strokeWidth="2" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center pt-1">
        <span className="text-3xl font-extrabold tracking-tight">{value === null ? '—' : `${value.toFixed(1)}%`}</span>
        <span className={`text-xs font-semibold ${met ? 'text-accent' : 'text-muted'}`}>
          {met ? `target ${target}% met` : `target ≥ ${target}%`}
        </span>
      </div>
    </div>
  )
}
