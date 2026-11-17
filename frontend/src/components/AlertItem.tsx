import { AlertTriangle, Clock, Info } from 'lucide-react'
import type { Alert } from '../lib/insights'
import { useT } from '../lib/i18n'
import { useSim } from '../store/simStore'

const TONE = {
  crit: { box: 'border-crit/25 bg-crit/[0.06]', icon: 'text-crit', Icon: AlertTriangle, sr: 'Urgent' as const },
  warn: { box: 'border-warn/25 bg-warn/[0.07]', icon: 'text-warn', Icon: Clock, sr: 'Warning' as const },
  info: { box: 'border-agent-demand/20 bg-agent-demand/[0.06]', icon: 'text-agent-demand', Icon: Info, sr: 'Info' as const },
}

/** One alert row; its action opens the price formula or the related tab. */
export default function AlertItem({ a, onAct }: { a: Alert; onAct?: () => void }) {
  const openFormula = useSim((s) => s.openFormula)
  const setPage = useSim((s) => s.setPage)
  const tr = useT()
  const t = TONE[a.tone]
  const action = a.skuId ? tr('See price') : a.goTo ? tr('Open') : null
  return (
    <li className={`flex items-start gap-3 rounded-xl border p-3 ${t.box}`}>
      <t.Icon size={20} aria-hidden className={`mt-0.5 shrink-0 ${t.icon}`} />
      <div className="min-w-0 flex-1">
        <div className="text-sm font-bold">
          <span className="sr-only">{tr(t.sr)}: </span>
          {a.title}
        </div>
        <div className={`text-xs ${a.tone === 'info' ? 'text-muted' : t.icon}`}>{a.detail}</div>
      </div>
      {action && (
        <button
          type="button"
          className="shrink-0 rounded-full bg-panel px-2.5 py-1 text-xs font-semibold shadow-sm hover:text-accent"
          onClick={() => {
            onAct?.()
            if (a.skuId) void openFormula(a.skuId)
            else if (a.goTo) setPage(a.goTo)
          }}
        >
          {action}
        </button>
      )}
    </li>
  )
}
