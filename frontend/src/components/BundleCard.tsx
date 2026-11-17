import { CheckCircle2, Clock, Gift, XCircle } from 'lucide-react'
import { simClock, usd } from '../lib/format'
import { useT } from '../lib/i18n'
import type { Bundle } from '../types/contracts'

const STATUS = {
  listed: { label: 'For sale', cls: 'text-accent', Icon: Gift },
  sold: { label: 'Sold', cls: 'text-ok', Icon: CheckCircle2 },
  expired: { label: 'Expired unsold', cls: 'text-crit', Icon: XCircle },
} as const

export default function BundleCard({ b }: { b: Bundle }) {
  const s = STATUS[b.status]
  const t = useT()
  const off = Math.round((1 - b.price / b.base_total) * 100)
  return (
    <article
      aria-label={`${t('Surplus box')} ${b.bundle_id}, ${t(s.label)}`}
      className={`rounded-md border border-line bg-panel-2 p-2.5 ${b.status === 'listed' ? '' : 'opacity-70'}`}
    >
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-mono text-muted">{b.bundle_id}</span>
        <span className={`flex items-center gap-1 ${s.cls}`}>
          <s.Icon size={12} aria-hidden />
          {t(s.label)}
        </span>
      </div>
      <ul className="my-1.5 text-xs">
        {b.items.map((i) => (
          <li key={i.sku_id} className="truncate">
            <span className="font-mono tabular-nums text-muted">{i.qty}×</span> {i.name}
          </li>
        ))}
      </ul>
      <div className="flex items-end justify-between">
        <div className="font-mono tabular-nums">
          <span className="text-base font-semibold">{usd(b.price)}</span>{' '}
          <span className="text-[11px] text-warn">−{off}%</span>
          <div className="text-[11px] text-muted line-through">{usd(b.base_total)}</div>
        </div>
        <div className="text-right font-mono text-[11px] tabular-nums text-muted">
          {b.status === 'listed' ? (
            <span className={`flex items-center gap-1 ${b.expires_in_hours < 3 ? 'text-crit' : ''}`}>
              <Clock size={11} aria-hidden />
              {t('{h} h left', { h: b.expires_in_hours.toFixed(1) })}
            </span>
          ) : (
            <span>{t('made {at}', { at: simClock(b.created_tick) })}</span>
          )}
        </div>
      </div>
    </article>
  )
}
