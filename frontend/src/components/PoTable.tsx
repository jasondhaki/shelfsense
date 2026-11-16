import { CloudRain } from 'lucide-react'
import { simClock } from '../lib/format'
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

  if (rows.length === 0) {
    return (
      <p className="p-4 text-sm text-muted">
        No purchase orders yet. ShelfSense plans tomorrow’s orders at 21:00, or straight away
        when the weather changes.
      </p>
    )
  }

  const total = (k: 'baseline_order' | 'ai_order' | 'waste_prevention_units') =>
    rows.reduce((s, r) => s + r[k], 0)
  const totalKg = rows.reduce((s, r) => s + r.waste_prevention_kg, 0)

  return (
    <table className="w-full border-collapse text-xs">
      <caption className="sr-only">Next purchase orders, baseline store vs ShelfSense</caption>
      <thead className="sticky top-0 bg-panel text-left text-[11px] text-muted">
        <tr className="[&>th]:px-2 [&>th]:py-1.5 [&>th]:font-normal">
          <th scope="col">Product</th>
          <th scope="col">Supplier</th>
          <th scope="col" className="text-right">Baseline order</th>
          <th scope="col" className="text-right">Carryover</th>
          <th scope="col" className="text-right">Weather</th>
          <th scope="col" className="text-right">ShelfSense order</th>
          <th scope="col" className="text-right">Waste prevented</th>
        </tr>
      </thead>
      <tbody className="font-mono tabular-nums">
        {rows.map((r) => {
          const before = regular[r.sku_id]
          const moved = r.reason !== null && before !== undefined && before !== r.ai_order
          return (
            <tr
              key={r.sku_id}
              className={`border-t border-line [&>td]:px-2 [&>td]:py-1.5 ${moved ? 'bg-agent-procurement/10' : ''}`}
            >
              <th scope="row" className="px-2 text-left font-mono font-normal">
                {r.sku_id}
                <div className="font-sans text-[10px] text-muted">
                  delivers {simClock(r.delivery_tick)}
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
                    {before} → {r.ai_order} after {r.reason}
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
            Total
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
  )
}
