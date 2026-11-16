import { X } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { simClock, usd } from '../lib/format'
import { useSim } from '../store/simStore'
import type { FormulaBreakdown } from '../types/contracts'

const n = (x: number, d = 1) => x.toFixed(d)
const pct = (x: number) => `${x > 0 ? '+' : ''}${x.toFixed(0)}%`

function Step({ label, formula, value }: { label: string; formula?: string; value: string }) {
  return (
    <li className="border-t border-line py-2 first:border-t-0">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-xs text-muted">{label}</span>
        <span className="font-mono text-sm tabular-nums">{value}</span>
      </div>
      {formula && <div className="mt-0.5 font-mono text-[11px] text-muted">{formula}</div>}
    </li>
  )
}

function Steps({ f, base }: { f: FormulaBreakdown; base: number }) {
  const risky = f.risk
  return (
    <ol>
      <Step
        label="Shelf life left (oldest batch)"
        formula={`(SL − age) ÷ (α ${n(f.alpha_known, 2)} × β ${n(f.beta_sku, 2)})`}
        value={`${n(f.rsl_known)} h`}
      />
      <Step label="Units on the shelf" value={String(f.inventory)} />
      <Step
        label="Sales needed to clear it in time"
        formula="V_target = units ÷ shelf life (tightest batch)"
        value={`${n(f.v_target, 2)} /h`}
      />
      <Step
        label="Sales expected at full price"
        formula={`V_forecast = average demand over the next ${Math.ceil(f.rsl_known)} h`}
        value={`${n(f.v_forecast, 2)} /h`}
      />
      {risky ? (
        <>
          <Step
            label="Extra sales needed"
            formula="ΔQ = (V_target − V_forecast) ÷ V_forecast"
            value={pct(f.delta_q_pct)}
          />
          <Step
            label="Price change to get there"
            formula={`ΔP = ΔQ ÷ ε, ε = ${n(f.elasticity)} (assumed, not measured)`}
            value={pct(f.delta_p_pct)}
          />
          <Step
            label="Raw price"
            formula={`${usd(base)} × (1 ${f.delta_p_pct < 0 ? '−' : '+'} ${n(Math.abs(f.delta_p_pct), 0)}%)`}
            value={usd(f.p_raw)}
          />
          <Step
            label="After the price floor"
            formula={`max(floor ${usd(f.p_floor)}, raw)${f.floor_bound ? ' — floor hit, item goes to a surplus box if still short' : ''}`}
            value={usd(f.p_new)}
          />
        </>
      ) : (
        <Step
          label="No surplus risk"
          formula="Expected sales clear the stock in time, so the price stays at base"
          value={usd(f.p_new)}
        />
      )}
      <Step
        label="Price on the shelf label"
        formula="Only republished when it moves ≥ 2% of base price"
        value={usd(f.p_current)}
      />
    </ol>
  )
}

export default function FormulaDrawer() {
  const sku = useSim((s) => s.selectedSku)
  const f = useSim((s) => s.formula)
  const esl = useSim((s) => s.snapshot?.esl.find((e) => e.sku_id === s.selectedSku))
  const tick = useSim((s) => s.snapshot?.tick)
  const open = useSim((s) => s.openFormula)
  const close = useSim((s) => s.closeFormula)
  const closeBtn = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (sku) closeBtn.current?.focus()
  }, [sku])

  useEffect(() => {
    if (sku) void open(sku) // keep the numbers in step with the live price
  }, [sku, tick, open])

  useEffect(() => {
    if (!sku) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [sku, close])

  return (
    <aside
      role="dialog"
      aria-modal="false"
      aria-label={esl ? `How ${esl.name} is priced` : 'Price formula'}
      aria-hidden={!sku}
      className={`fixed bottom-2 right-2 top-[104px] z-30 flex w-[380px] max-w-[calc(100vw-1rem)] flex-col rounded-lg border border-line bg-panel shadow-2xl transition-transform duration-200 ${
        sku ? 'translate-x-0' : 'pointer-events-none translate-x-[110%]'
      }`}
    >
      <div className="flex items-start justify-between border-b border-line p-3">
        <div>
          <div className="font-mono text-[11px] text-muted">{esl?.sku_id}</div>
          <h2 className="text-sm font-medium">How this price was set</h2>
          <div className="text-xs text-muted">
            {esl?.name}
            {f && ` · computed ${simClock(f.tick)}`}
          </div>
        </div>
        <button
          ref={closeBtn}
          type="button"
          className="btn-icon"
          aria-label="Close price formula"
          tabIndex={sku ? 0 : -1}
          onClick={close}
        >
          <X size={16} aria-hidden />
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {!f || !esl ? (
          <p className="text-sm text-muted">Loading the numbers…</p>
        ) : (
          <>
            <Steps f={f} base={esl.base_price} />
            <div className="mt-4 rounded-md bg-panel-2 p-2.5 text-[11px] text-muted">
              <div className="mb-1 font-medium text-text">Where the inputs come from</div>
              <ul className="list-disc space-y-0.5 pl-4">
                {f.sources.map((s) => (
                  <li key={s}>{s}</li>
                ))}
                <li>Demand forecast: Kaggle Favorita weekday pattern × assumed hourly curve</li>
              </ul>
            </div>
          </>
        )}
      </div>
    </aside>
  )
}
