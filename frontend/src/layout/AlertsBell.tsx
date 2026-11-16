import { Bell } from 'lucide-react'
import { useCallback, useRef, useState } from 'react'
import AlertItem from '../components/AlertItem'
import { deriveAlerts } from '../lib/insights'
import { useDismiss } from '../lib/useDismiss'
import { useSim } from '../store/simStore'

export default function AlertsBell() {
  const snap = useSim((s) => s.snapshot)
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const close = useCallback(() => setOpen(false), [])
  useDismiss(root, open, close)

  const alerts = snap ? deriveAlerts(snap) : []
  const urgent = alerts.filter((a) => a.tone !== 'info').length

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        className="relative grid h-11 w-11 place-items-center rounded-full text-text hover:bg-panel"
        aria-label={`Alerts: ${alerts.length}${urgent ? `, ${urgent} urgent` : ''}`}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <Bell size={24} aria-hidden strokeWidth={1.8} />
        {alerts.length > 0 && (
          <span
            className={`absolute right-1 top-1 grid h-5 min-w-5 place-items-center rounded-full px-1 text-[10px] font-bold text-white ${urgent ? 'bg-crit' : 'bg-accent'}`}
            aria-hidden
          >
            {alerts.length}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-[min(360px,calc(100vw-2rem))] rounded-2xl border border-line bg-panel p-3 shadow-card">
          <h2 className="mb-2 px-1 text-sm font-bold">Real-time alerts</h2>
          {alerts.length === 0 ? (
            <p className="px-1 pb-1 text-sm text-muted">All clear. Alerts show up when stock nears expiry or orders change.</p>
          ) : (
            <ul className="max-h-[60vh] space-y-2 overflow-y-auto">
              {alerts.map((a) => (
                <AlertItem key={a.id} a={a} onAct={close} />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
