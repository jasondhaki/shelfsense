import { Bell } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import AlertItem from '../components/AlertItem'
import { deriveAlerts } from '../lib/insights'
import { useDismiss } from '../lib/useDismiss'
import { useT } from '../lib/i18n'
import { useSim } from '../store/simStore'

export default function AlertsBell() {
  const snap = useSim((s) => s.snapshot)
  const t = useT()
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const close = useCallback(() => setOpen(false), [])
  useDismiss(root, open, close)

  const seen = useSim((s) => s.seenAlerts)
  const setSeen = useSim((s) => s.setSeenAlerts)

  const alerts = snap ? deriveAlerts(snap, t) : []
  const unread = alerts.filter((a) => !seen.includes(a.id))
  const urgent = unread.filter((a) => a.tone !== 'info').length
  const ids = alerts.map((a) => a.id).join('|')

  // while the panel is open, everything in it counts as read
  useEffect(() => {
    if (open) setSeen(ids ? ids.split('|') : [])
  }, [open, ids, setSeen])

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        className="relative grid h-11 w-11 place-items-center rounded-full text-text hover:bg-panel"
        aria-label={t(urgent ? 'Alerts: {n}, {u} urgent' : 'Alerts: {n}', { n: unread.length, u: urgent })}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <Bell size={24} aria-hidden strokeWidth={1.8} />
        {unread.length > 0 && (
          <span
            className={`absolute right-1 top-1 grid h-5 min-w-5 place-items-center rounded-full px-1 text-[10px] font-bold text-white dark:text-forest-950 ${urgent ? 'bg-crit' : 'bg-accent'}`}
            aria-hidden
          >
            {unread.length}
          </span>
        )}
      </button>
      {open && (
        <div className="fixed inset-x-3 top-28 z-30 rounded-2xl border border-line bg-panel p-3 shadow-card sm:absolute sm:inset-x-auto sm:right-0 sm:top-auto sm:mt-2 sm:w-[360px]">
          <h2 className="mb-2 px-1 text-sm font-bold">{t('Real-time alerts')}</h2>
          {alerts.length === 0 ? (
            <p className="px-1 pb-1 text-sm text-muted">{t('All clear. Alerts show up when stock nears expiry or orders change.')}</p>
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
