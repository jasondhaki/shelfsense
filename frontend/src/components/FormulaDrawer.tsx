import { X } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { simClock, usd } from '../lib/format'
import { useT, type T } from '../lib/i18n'
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

function Steps({ f, base, t }: { f: FormulaBreakdown; base: number; t: T }) {
  const risky = f.risk
  return (
    <ol>
      <Step
        label={t('Shelf life left (oldest batch)')}
        formula={`(SL − age) ÷ (α ${n(f.alpha_known, 2)} × β ${n(f.beta_sku, 2)})`}
        value={`${n(f.rsl_known)} h`}
      />
      <Step label={t('Units on the shelf')} value={String(f.inventory)} />
      <Step
        label={t('Sales needed to clear it in time')}
        formula={`V_target = ${t('units ÷ shelf life (tightest batch)')}`}
        value={`${n(f.v_target, 2)} /h`}
      />
      <Step
        label={t('Sales expected at full price')}
        formula={`V_forecast = ${t('average demand over the next {h} h', { h: Math.ceil(f.rsl_known) })}`}
        value={`${n(f.v_forecast, 2)} /h`}
      />
      {risky ? (
        <>
          <Step
            label={t('Extra sales needed')}
            formula="ΔQ = (V_target − V_forecast) ÷ V_forecast"
            value={pct(f.delta_q_pct)}
          />
          <Step
            label={t('Price change to get there')}
            formula={`ΔP = ΔQ ÷ ε, ε = ${n(f.elasticity)} ${t('(assumed, not measured)')}`}
            value={pct(f.delta_p_pct)}
          />
          <Step
            label={t('Raw price')}
            formula={`${usd(base)} × (1 ${f.delta_p_pct < 0 ? '−' : '+'} ${n(Math.abs(f.delta_p_pct), 0)}%)`}
            value={usd(f.p_raw)}
          />
          <Step
            label={t('After the price floor')}
            formula={`max(${t('floor')} ${usd(f.p_floor)}, ${t('raw')})${f.floor_bound ? ` — ${t('floor hit, item goes to a surplus box if still short')}` : ''}`}
            value={usd(f.p_new)}
          />
        </>
      ) : (
        <Step
          label={t('No surplus risk')}
          formula={t('Expected sales clear the stock in time, so the price stays at base')}
          value={usd(f.p_new)}
        />
      )}
      <Step
        label={t('Price on the shelf label')}
        formula={t('Only republished when it moves ≥ 2% of base price')}
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
  const t = useT()

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
      aria-label={esl ? t('How {name} is priced', { name: esl.name }) : t('Price formula')}
      aria-hidden={!sku}
      className={`fixed inset-x-2 bottom-2 z-30 flex max-h-[78vh] flex-col rounded-2xl border border-line bg-panel shadow-2xl transition-transform duration-200 sm:inset-x-auto sm:right-2 sm:top-[104px] sm:max-h-none sm:w-[380px] ${
        sku ? 'translate-x-0 translate-y-0' : 'pointer-events-none translate-y-[110%] sm:translate-x-[110%] sm:translate-y-0'
      }`}
    >
      <div className="flex items-start justify-between border-b border-line p-3">
        <div>
          <div className="font-mono text-[11px] text-muted">{esl?.sku_id}</div>
          <h2 className="text-sm font-medium">{t('How this price was set')}</h2>
          <div className="text-xs text-muted">
            {esl?.name}
            {f && ` · ${t('computed {at}', { at: simClock(f.tick) })}`}
          </div>
        </div>
        <button
          ref={closeBtn}
          type="button"
          className="btn-icon"
          aria-label={t('Close price formula')}
          tabIndex={sku ? 0 : -1}
          onClick={close}
        >
          <X size={16} aria-hidden />
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {!f || !esl ? (
          <p className="text-sm text-muted">{t('Loading the numbers…')}</p>
        ) : (
          <>
            <Steps f={f} base={esl.base_price} t={t} />
            <div className="mt-4 rounded-md bg-panel-2 p-2.5 text-[11px] text-muted">
              <div className="mb-1 font-medium text-text">{t('Where the inputs come from')}</div>
              <ul className="list-disc space-y-0.5 pl-4">
                {f.sources.map((s) => (
                  <li key={s}>{s}</li>
                ))}
                <li>{t('Demand forecast: Kaggle Favorita weekday pattern × assumed hourly curve')}</li>
              </ul>
            </div>
          </>
        )}
      </div>
    </aside>
  )
}
