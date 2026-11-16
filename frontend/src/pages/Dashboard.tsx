import { ArrowRight, CircleDollarSign, Cloud, ShoppingBasket, Sprout } from 'lucide-react'
import { lazy, Suspense } from 'react'
import AlertItem from '../components/AlertItem'
import FreshnessHero from '../components/FreshnessHero'
import Gauge from '../components/Gauge'
import InventoryTable from '../components/InventoryTable'
import StatCard from '../components/StatCard'
import { usd } from '../lib/format'
import { activeAgents, AGENT_CHIPS, dayChange, deriveAlerts, series, type KpiKey } from '../lib/insights'
import { useSim } from '../store/simStore'

const DemandWasteCard = lazy(() => import('../components/DemandWasteCard'))

const TARGET = 30

function AgentsCard() {
  const logs = useSim((s) => s.logs)
  const tick = useSim((s) => s.snapshot?.tick ?? 0)
  const setPage = useSim((s) => s.setPage)
  const active = activeAgents(logs, tick)
  const last = [...logs].reverse().find((l) => l.agent !== 'SYSTEM')
  const chip = AGENT_CHIPS.find((c) => c.agent === last?.agent)
  return (
    <section aria-labelledby="ag-title" className="zone p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 id="ag-title" className="h-card">
          Insight &amp; agents
        </h2>
        <button type="button" className="link" onClick={() => setPage('agents')}>
          Reasoning log <ArrowRight size={14} aria-hidden />
        </button>
      </div>
      <p className="mt-1 text-sm text-muted">Workforce: {active.size ? `${[...active].filter((a) => a !== 'SYSTEM').length} agents active in the last 6 h` : 'agents idle until the week runs'}</p>
      <ul className="mt-3 flex flex-wrap gap-2">
        {AGENT_CHIPS.slice(0, 4).map((c) => {
          const on = active.has(c.agent)
          return (
            <li key={c.agent} className="chip border-line bg-panel-2">
              <span className={c.tone}>{c.label}</span>
              <span className={`h-2 w-2 rounded-full ${on ? 'bg-ok' : 'bg-baseline/50'}`} aria-hidden />
              <span className="sr-only">{on ? 'active' : 'idle'}</span>
            </li>
          )
        })}
      </ul>
      {last && (
        <p className="mt-3 line-clamp-2 rounded-xl bg-panel-2 px-3 py-2 text-xs">
          <span className={`font-bold ${chip?.tone ?? 'text-muted'}`}>{chip?.label ?? last.agent}</span>{' '}
          <span className="text-muted">[{last.sim_time}]</span> {last.message}
        </p>
      )}
    </section>
  )
}

function AlertsCard() {
  const snap = useSim((s) => s.snapshot)
  const alerts = snap ? deriveAlerts(snap) : []
  return (
    <section aria-labelledby="al-title" className="zone p-4">
      <h2 id="al-title" className="h-card">
        Real-time alerts
      </h2>
      {alerts.length === 0 ? (
        <p className="mt-2 text-sm text-muted">All clear. Alerts appear when stock nears expiry or orders change.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {alerts.slice(0, 3).map((a) => (
            <AlertItem key={a.id} a={a} />
          ))}
        </ul>
      )}
    </section>
  )
}

export default function Dashboard() {
  const snap = useSim((s) => s.snapshot)
  const which = useSim((s) => s.eslStore)
  if (!snap) return <div className="zone h-96 animate-pulse" aria-busy />

  const k = snap.kpis
  const ch = snap.chart
  const change = (key: KpiKey, fmt: (n: number) => string) => {
    const d = dayChange(ch, key)
    return d === null ? null : { value: d, text: fmt(Math.abs(d)) }
  }
  const rows = which === 'A' ? snap.esl_a : snap.esl

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <div className="grid grid-cols-2 gap-3 sm:gap-4">
          <StatCard
            label="Waste reduction"
            value={k.waste_reduction_pct}
            format={(n) => `${n.toFixed(1)}%`}
            change={change('reduction', (n) => `${n.toFixed(1)} pp`)}
            history={series(ch, 'reduction')}
            Icon={Sprout}
            tile="bg-mint text-accent"
            color="#0F7B57"
            hint="Food wasted by this store vs its baseline twin, same shoppers"
          />
          <StatCard
            label="Food diverted"
            value={k.food_diverted_kg}
            format={(n) => `${n.toFixed(1)} kg`}
            change={change('diverted', (n) => `${n.toFixed(1)} kg`)}
            history={series(ch, 'diverted')}
            Icon={ShoppingBasket}
            tile="bg-[#DDF4F1] text-[#0F766E]"
            color="#14B8A6"
            hint="Kilograms the baseline store threw away that this store sold instead"
          />
          <StatCard
            label="CO₂e avoided"
            value={k.co2e_avoided_kg}
            format={(n) => `${n.toFixed(1)} kg`}
            change={change('co2e', (n) => `${n.toFixed(1)} kg`)}
            history={series(ch, 'co2e')}
            Icon={Cloud}
            tile="bg-[#EFE9FE] text-[#7C3AED]"
            color="#A78BFA"
            hint="Diverted food × category emission factors (Poore & Nemecek 2018)"
          />
          <StatCard
            label="Net margin recovered"
            value={k.net_margin_recovered_usd}
            format={usd}
            change={change('margin', (n) => usd(n))}
            history={series(ch, 'margin')}
            Icon={CircleDollarSign}
            tile="bg-[#FEF3C7] text-[#B45309]"
            color="#F59E0B"
            hint="Gross margin of this store minus the baseline store's"
          />
        </div>
        <FreshnessHero />
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <InventoryTable rows={rows} limit={8} />
        <div className="space-y-5">
          <AgentsCard />
          <Suspense fallback={<div className="zone h-[320px]" aria-busy />}>
            <DemandWasteCard esl={snap.esl} chart={ch} />
          </Suspense>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
            <AlertsCard />
            <section aria-labelledby="wr-title" className="zone flex flex-col items-center p-4">
              <h2 id="wr-title" className="h-card self-start">
                Waste reduction progress
              </h2>
              <div className="mt-2 w-full">
                <Gauge value={k.waste_reduction_pct} target={TARGET} />
              </div>
              <p className="mt-1 text-center text-xs text-muted">
                {k.waste_kg_b.toFixed(1)} kg wasted vs {k.waste_kg_a.toFixed(1)} kg at the baseline
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}
