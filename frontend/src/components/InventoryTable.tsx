import { AlertTriangle, ArrowRight, Clock, Tag } from 'lucide-react'
import { useState } from 'react'
import { usd } from '../lib/format'
import { atRisk, freshness, NUTRI, productImg } from '../lib/insights'
import { useSim } from '../store/simStore'
import type { EslView } from '../types/contracts'

type Filter = 'all' | 'risk' | 'discounted'

function Countdown({ e }: { e: EslView }) {
  if (!e.on_hand) return <span className="text-xs font-semibold text-muted">Sold out</span>
  const h = e.rsl_hours
  const tone = h < 8 ? 'bg-crit/10 text-crit' : h < 24 ? 'bg-warn/10 text-warn' : 'bg-mint text-accent'
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ${tone}`}>
      <Clock size={13} aria-hidden />
      {h < 8 && <span className="sr-only">Critical: </span>}
      Expires: {h < 48 ? `${h.toFixed(h < 10 ? 1 : 0)} h` : `${(h / 24).toFixed(1)} d`}
    </span>
  )
}

function Fresh({ e }: { e: EslView }) {
  const f = freshness(e)
  const bar = f < 0.15 ? 'bg-crit' : f < 0.3 ? 'bg-warn' : 'bg-accent'
  return (
    <div className="flex items-center gap-2" title={`${e.rsl_hours.toFixed(1)} h left of ${e.shelf_life_hours} h nominal shelf life`}>
      <div className="h-2 w-20 overflow-hidden rounded-full bg-line" aria-hidden>
        <div className={`h-full rounded-full ${bar}`} style={{ width: `${f * 100}%` }} />
      </div>
      <span className="w-9 text-right text-sm font-semibold">{e.on_hand ? `${Math.round(f * 100)}%` : '—'}</span>
    </div>
  )
}

interface Props {
  rows: EslView[]
  /** Dashboard shows the most urgent few and a "View all" link; the Inventory page shows all. */
  limit?: number
  detailed?: boolean
}

export default function InventoryTable({ rows, limit, detailed = false }: Props) {
  const [filter, setFilter] = useState<Filter>('all')
  const which = useSim((s) => s.eslStore)
  const openFormula = useSim((s) => s.openFormula)
  const setPage = useSim((s) => s.setPage)

  const riskCount = rows.filter(atRisk).length
  const discCount = rows.filter((e) => e.markdown_pct > 0.005).length
  const shown = rows
    .filter((e) => (filter === 'risk' ? atRisk(e) : filter === 'discounted' ? e.markdown_pct > 0.005 : true))
    .sort((a, b) => (a.on_hand ? a.rsl_hours : 1e9) - (b.on_hand ? b.rsl_hours : 1e9))
    .slice(0, limit)

  const FILTERS: { id: Filter; label: string; Icon?: typeof Tag; iconCls?: string }[] = [
    { id: 'all', label: 'All items' },
    { id: 'risk', label: `At risk (${riskCount})`, Icon: AlertTriangle, iconCls: 'text-warn' },
    { id: 'discounted', label: `Discounted (${discCount})`, Icon: Tag, iconCls: 'text-warn' },
  ]

  return (
    <section aria-labelledby="inv-title" className="zone flex flex-col p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 id="inv-title" className="h-card">
            Shelf inventory &amp; quick actions
          </h2>
          <p className="text-sm text-muted">
            Live stock, freshness and spoilage risk{which === 'A' ? ' — baseline store (printed dates only)' : ''}.
          </p>
        </div>
        {limit && (
          <button type="button" className="link shrink-0" onClick={() => setPage('inventory')}>
            View all <ArrowRight size={14} aria-hidden />
          </button>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Filter items">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            aria-pressed={filter === f.id}
            onClick={() => setFilter(f.id)}
            className={`chip ${filter === f.id ? 'border-forest-800 bg-forest-800 text-white' : 'border-line bg-panel text-text hover:border-accent/60'}`}
          >
            {f.Icon && <f.Icon size={14} aria-hidden className={filter === f.id ? '' : f.iconCls} />}
            {f.label}
          </button>
        ))}
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[620px] border-separate border-spacing-y-1.5 text-sm">
          <caption className="sr-only">Shelf items sorted by shelf life left</caption>
          <thead>
            <tr className="text-left text-xs font-semibold text-muted">
              <th scope="col" className="rounded-l-lg bg-panel-2 px-3 py-2">Product</th>
              <th scope="col" className="bg-panel-2 px-2 py-2 text-center">On shelf</th>
              {detailed && <th scope="col" className="bg-panel-2 px-2 py-2 text-center">Next 24 h demand</th>}
              <th scope="col" className="bg-panel-2 px-2 py-2">Countdown</th>
              <th scope="col" className="bg-panel-2 px-2 py-2">Freshness</th>
              <th scope="col" className="rounded-r-lg bg-panel-2 px-3 py-2 text-right">Price</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((e) => {
              const nutri = e.nutri_score?.toLowerCase()
              const marked = e.markdown_pct > 0.005
              const clickable = which === 'B'
              return (
                <tr
                  key={e.sku_id}
                  onClick={clickable ? () => openFormula(e.sku_id) : undefined}
                  className={`group ${clickable ? 'cursor-pointer' : ''}`}
                >
                  <td className="rounded-l-xl border-y border-l border-line/70 bg-panel px-3 py-2 group-hover:bg-panel-2">
                    <div className="flex items-center gap-3">
                      <img src={productImg(e.sku_id)} alt="" className="h-12 w-12 shrink-0 rounded-lg object-cover" loading="lazy" />
                      <div className="min-w-0">
                        {clickable ? (
                          <button
                            type="button"
                            className="block truncate text-left font-semibold hover:text-accent"
                            onClick={(ev) => {
                              ev.stopPropagation()
                              void openFormula(e.sku_id)
                            }}
                            aria-label={`${e.name}: see how its price is set`}
                          >
                            {e.name}
                          </button>
                        ) : (
                          <div className="truncate font-semibold">{e.name}</div>
                        )}
                        <div className="text-xs text-muted">{e.sku_id}</div>
                      </div>
                      <span
                        title={nutri ? `Nutri-Score ${nutri.toUpperCase()}` : 'Nutri-Score not available'}
                        className={`ml-auto grid h-7 w-7 shrink-0 place-items-center rounded-md text-xs font-bold ${nutri && NUTRI[nutri] ? NUTRI[nutri] : 'bg-line text-muted'}`}
                      >
                        {nutri ? nutri.toUpperCase() : '–'}
                      </span>
                    </div>
                  </td>
                  <td className="border-y border-line/70 bg-panel px-2 py-2 text-center text-base font-semibold group-hover:bg-panel-2">
                    {e.on_hand}
                  </td>
                  {detailed && (
                    <td className="border-y border-line/70 bg-panel px-2 py-2 text-center group-hover:bg-panel-2">
                      {e.forecast_24h.toFixed(0)}
                      {e.surplus_risk_units > 0 && (
                        <div className="text-[11px] font-semibold text-warn">{e.surplus_risk_units} surplus</div>
                      )}
                    </td>
                  )}
                  <td className="border-y border-line/70 bg-panel px-2 py-2 group-hover:bg-panel-2">
                    <Countdown e={e} />
                  </td>
                  <td className="border-y border-line/70 bg-panel px-2 py-2 group-hover:bg-panel-2">
                    <Fresh e={e} />
                  </td>
                  <td className="rounded-r-xl border-y border-r border-line/70 bg-panel px-3 py-2 text-right group-hover:bg-panel-2">
                    {marked && (
                      <div className="text-xs text-muted">
                        <span className="line-through">{usd(e.base_price)}</span>{' '}
                        <span className="font-bold text-warn">−{Math.round(e.markdown_pct * 100)}%</span>
                      </div>
                    )}
                    <div className="text-lg font-extrabold">{usd(e.current_price)}</div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {shown.length === 0 && (
          <p className="py-6 text-center text-sm text-muted">
            {filter === 'risk' ? 'Nothing at risk right now.' : 'No items are discounted right now.'}
          </p>
        )}
      </div>
    </section>
  )
}
