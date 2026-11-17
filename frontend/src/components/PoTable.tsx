import { CloudRain } from 'lucide-react'
import { simClock } from '../lib/format'
import { useT } from '../lib/i18n'
import type { PoRow } from '../types/contracts'

/** Store B's next purchase orders vs what the baseline store would order (SIMULATION_ENGINE §7.4). */
export default function PoTable({
  rows,
  regular,
}: {
  rows: PoRow[]
  /** ShelfSense orders from the last regular run, keyed by SKU. */
  regular: Record<string, number>
}) {
  const t = useT()

  if (rows.length === 0) {
    return (
      <p className="p-4 text-sm text-muted">
        {t('No purchase orders yet. ShelfSense plans tomorrow’s orders at 21:00, or straight away when the weather changes.')}
      </p>
    )
  }

  const total = (k: 'baseline_order' | 'ai_order' | 'waste_prevention_units') =>
    rows.reduce((s, r) => s + r[k], 0)
  const totalKg = rows.reduce((s, r) => s + r.waste_prevention_kg, 0)

  return (
    <>
    {/* phones: one card per product */}
    <ul className="divide-y divide-line md:hidden">
      {rows.map((r) => {
        const before = regular[r.sku_id]
        const moved = r.reason !== null && before !== undefined && before !== r.ai_order
        return (
          <li key={r.sku_id} className={`p-3 ${moved ? 'bg-agent-procurement/10' : ''}`}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-sm font-bold">{r.sku_id}</div>
                <div className="truncate text-xs text-muted">
                  {r.supplier} · {t('delivers {at}', { at: simClock(r.delivery_tick) })}
                </div>
              </div>
              <div className="shrink-0 text-right">
                <div className="text-lg font-extrabold leading-tight">{r.ai_order}</div>
                <div className="text-[11px] text-muted">{t('baseline {n}', { n: r.baseline_order })}</div>
              </div>
            </div>
            {moved && (
              <div className="mt-1 inline-flex items-center gap-1 rounded-full bg-agent-procurement/15 px-2 py-0.5 text-[11px] text-agent-procurement">
                <CloudRain size={11} aria-hidden />
                {before} → {r.ai_order} {t('after')} {r.reason}
              </div>
            )}
            <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-muted">
              <span>{t('carryover {n}', { n: r.projected_carryover })}</span>
              <span>{t('weather')} ×{r.weather_modifier.toFixed(2)}</span>
              <span className={r.waste_prevention_units > 0 ? 'font-semibold text-ok' : ''}>
                {t('waste prevented')} {r.waste_prevention_units > 0 ? '+' : ''}
                {r.waste_prevention_units} · {r.waste_prevention_kg.toFixed(1)} kg
              </span>
            </div>
          </li>
        )
      })}
      <li className="flex justify-between p-3 text-sm font-bold">
        <span>{t('Total')}</span>
        <span>
          {total('ai_order')} <span className="text-xs font-semibold text-muted">{t('vs baseline {n}', { n: total('baseline_order') })}</span>
        </span>
      </li>
    </ul>
    <table className="hidden w-full border-collapse text-sm md:table">
      <caption className="sr-only">{t('Next purchase orders, baseline store vs ShelfSense')}</caption>
      <thead className="sticky top-0 bg-panel text-left text-xs text-muted">
        <tr className="[&>th]:px-3 [&>th]:py-2.5 [&>th]:font-semibold">
          <th scope="col">{t('Product')}</th>
          <th scope="col">{t('Supplier')}</th>
          <th scope="col" className="text-right">{t('Baseline order')}</th>
          <th scope="col" className="text-right">{t('Carryover')}</th>
          <th scope="col" className="text-right">{t('Weather')}</th>
          <th scope="col" className="text-right">{t('ShelfSense order')}</th>
          <th scope="col" className="text-right">{t('Waste prevented')}</th>
        </tr>
      </thead>
      <tbody className="font-mono tabular-nums">
        {rows.map((r) => {
          const before = regular[r.sku_id]
          const moved = r.reason !== null && before !== undefined && before !== r.ai_order
          return (
            <tr
              key={r.sku_id}
              className={`border-t border-line [&>td]:px-3 [&>td]:py-2.5 ${moved ? 'bg-agent-procurement/10' : ''}`}
            >
              <th scope="row" className="px-3 text-left font-semibold">
                {r.sku_id}
                <div className="font-sans text-[10px] text-muted">
                  {t('delivers {at}', { at: simClock(r.delivery_tick) })}
                </div>
              </th>
              <td className="font-sans text-muted">{r.supplier}</td>
              <td className="text-right text-muted">{r.baseline_order}</td>
              <td className="text-right">{r.projected_carryover}</td>
              <td className="text-right">×{r.weather_modifier.toFixed(2)}</td>
              <td className="text-right font-semibold">
                {moved && (
                  <span className="mr-1.5 inline-flex items-center gap-1 rounded-sm bg-agent-procurement/15 px-1 font-sans text-[10px] font-normal text-agent-procurement">
                    <CloudRain size={10} aria-hidden />
                    {before} → {r.ai_order} {t('after')} {r.reason}
                  </span>
                )}
                {r.ai_order}
              </td>
              <td className={`whitespace-nowrap text-right ${r.waste_prevention_units > 0 ? 'text-ok' : 'text-muted'}`}>
                {r.waste_prevention_units > 0 ? '+' : ''}
                {r.waste_prevention_units} · {r.waste_prevention_kg.toFixed(1)} kg
              </td>
            </tr>
          )
        })}
      </tbody>
      <tfoot className="font-mono tabular-nums">
        <tr className="border-t border-line text-muted [&>td]:px-2 [&>td]:py-1.5">
          <th scope="row" className="px-2 text-left font-sans font-normal" colSpan={2}>
            {t('Total')}
          </th>
          <td className="text-right">{total('baseline_order')}</td>
          <td />
          <td />
          <td className="text-right text-text">{total('ai_order')}</td>
          <td className="text-right">
            {total('waste_prevention_units')} · {totalKg.toFixed(1)} kg
          </td>
        </tr>
      </tfoot>
    </table>
    </>
  )
}
