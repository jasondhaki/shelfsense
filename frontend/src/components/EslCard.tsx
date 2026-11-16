import { AlertTriangle, Ban, Clock, Gift, Leaf, Package, TrendingDown } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { EslView, RiskState } from '../types/contracts'
import { usd } from '../lib/format'

const NUTRI: Record<string, string> = {
  a: 'bg-[#038141] text-white',
  b: 'bg-[#85BB2F] text-black',
  c: 'bg-[#FECB02] text-black',
  d: 'bg-[#EE8100] text-black',
  e: 'bg-[#E63E11] text-white',
}

const RIBBON: Record<Exclude<RiskState, 'ok'>, { label: string; cls: string; Icon: typeof Ban }> = {
  surplus_risk: { label: 'Surplus risk', cls: 'bg-warn/15 text-warn', Icon: TrendingDown },
  floor_bound: { label: 'At price floor', cls: 'bg-crit/15 text-crit', Icon: AlertTriangle },
  bundled: { label: 'In a surplus box', cls: 'bg-accent/15 text-accent', Icon: Gift },
  sold_out: { label: 'Sold out', cls: 'bg-line text-muted', Icon: Ban },
}

function rslTone(h: number): string {
  if (h < 8) return 'text-crit motion-safe:animate-pulse'
  if (h < 24) return 'text-warn'
  return 'text-text'
}

/** Inventory vs 24 h forecast: bar = stock, tick mark = forecast, red tail = surplus at risk. */
function StockBar({ esl }: { esl: EslView }) {
  const scale = Math.max(esl.on_hand, esl.forecast_24h, 1) * 1.1
  const pct = (n: number) => `${(n / scale) * 100}%`
  const safe = Math.max(esl.on_hand - esl.surplus_risk_units, 0)
  return (
    <div>
      <div className="relative h-2 overflow-hidden rounded-sm bg-line" aria-hidden>
        <div className="absolute inset-y-0 left-0 bg-baseline/70" style={{ width: pct(safe) }} />
        <div
          className="absolute inset-y-0 bg-crit"
          style={{ left: pct(safe), width: pct(esl.surplus_risk_units) }}
        />
        <div
          className="absolute inset-y-[-2px] w-0.5 bg-text"
          style={{ left: pct(esl.forecast_24h) }}
        />
      </div>
      <div className="mt-1 flex justify-between font-mono text-[11px] tabular-nums text-muted">
        <span>{esl.on_hand} on shelf</span>
        <span>{esl.forecast_24h.toFixed(0)} sell in 24 h</span>
      </div>
      {esl.surplus_risk_units > 0 && (
        <div className="font-mono text-[11px] tabular-nums text-crit">
          {esl.surplus_risk_units} won’t sell within 24 h
        </div>
      )}
    </div>
  )
}

export default function EslCard({ esl, onOpen }: { esl: EslView; onOpen?: () => void }) {
  const [flash, setFlash] = useState(false)
  const prev = useRef(esl.current_price)
  useEffect(() => {
    if (prev.current === esl.current_price) return
    prev.current = esl.current_price
    setFlash(true)
    const t = window.setTimeout(() => setFlash(false), 700)
    return () => window.clearTimeout(t)
  }, [esl.current_price])

  const ribbon = esl.risk_state === 'ok' ? null : RIBBON[esl.risk_state]
  const marked = esl.markdown_pct > 0.005
  const nutri = esl.nutri_score?.toLowerCase()
  const Wrapper = onOpen ? 'button' : 'article'

  return (
    <Wrapper
      {...(onOpen
        ? {
            type: 'button' as const,
            onClick: onOpen,
            'aria-label': `${esl.name}: ${usd(esl.current_price)}. Open the price formula.`,
          }
        : { 'aria-label': `${esl.name}: ${usd(esl.current_price)}` })}
      className={`group relative flex flex-col gap-2.5 overflow-hidden rounded-md border border-line bg-panel-2 p-3 text-left transition-colors ${onOpen ? 'hover:border-accent/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent' : ''}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-mono text-[11px] text-muted">{esl.sku_id}</div>
          <div className="truncate text-sm font-medium">{esl.name}</div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <span
            title={nutri ? `Nutri-Score ${nutri.toUpperCase()}` : 'Nutri-Score n/a'}
            className={`grid h-5 w-5 place-items-center rounded-sm text-[11px] font-bold ${nutri && NUTRI[nutri] ? NUTRI[nutri] : 'bg-line text-muted'}`}
          >
            {nutri ? nutri.toUpperCase() : '–'}
          </span>
          <span title={esl.packaging ?? 'Packaging n/a'} className="text-muted">
            <Package size={14} aria-hidden />
          </span>
          {esl.ethylene && esl.ethylene !== 'neutral' && (
            <span
              title={esl.ethylene === 'producer' ? 'Ethylene producer' : 'Ethylene sensitive'}
              className="flex items-center gap-0.5 rounded-sm bg-line px-1 text-[10px] text-muted"
            >
              <Leaf size={11} aria-hidden />
              {esl.ethylene === 'producer' ? 'emits' : 'sensitive'}
            </span>
          )}
        </div>
      </div>

      <StockBar esl={esl} />

      <div className="flex items-end justify-between">
        <div>
          <div className="text-[11px] text-muted">Shelf life left</div>
          <div className={`flex items-center gap-1 font-mono text-base tabular-nums ${rslTone(esl.rsl_hours)}`}>
            {esl.on_hand > 0 && esl.rsl_hours < 24 && (
              <Clock size={13} aria-hidden className={esl.rsl_hours < 8 ? 'hidden' : ''} />
            )}
            {esl.on_hand > 0 && esl.rsl_hours < 8 && <AlertTriangle size={13} aria-hidden />}
            {esl.on_hand ? `${esl.rsl_hours.toFixed(1)} h` : '—'}
            {esl.on_hand > 0 && esl.rsl_hours < 24 && (
              <span className="sr-only">{esl.rsl_hours < 8 ? '(critical)' : '(under a day)'}</span>
            )}
          </div>
          <div className="font-mono text-[11px] tabular-nums text-muted">
            label says {esl.on_hand ? `${Math.max(esl.printed_remaining_hours, 0).toFixed(0)} h` : '—'}
          </div>
        </div>
        <div className="text-right">
          {marked && (
            <div className="flex items-center justify-end gap-1.5">
              <span className="font-mono text-xs tabular-nums text-muted line-through">
                {usd(esl.base_price)}
              </span>
              <span className="rounded-sm bg-warn/15 px-1 font-mono text-[11px] tabular-nums text-warn">
                −{Math.round(esl.markdown_pct * 100)}%
              </span>
            </div>
          )}
          <div
            className={`font-mono text-3xl font-semibold leading-none tabular-nums transition-colors duration-700 ${flash ? 'text-accent' : 'text-text'}`}
          >
            {usd(esl.current_price)}
          </div>
          <div className="mt-1 font-mono text-[11px] tabular-nums text-muted">
            baseline store {usd(esl.store_a_price)}
          </div>
        </div>
      </div>

      {ribbon && (
        <div
          className={`-mx-3 -mb-3 flex items-center gap-1.5 px-3 py-1 text-[11px] font-medium ${ribbon.cls}`}
        >
          <ribbon.Icon size={12} aria-hidden />
          {ribbon.label}
        </div>
      )}
    </Wrapper>
  )
}
