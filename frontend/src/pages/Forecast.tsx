import { CloudRain, Droplets, Footprints, Thermometer } from 'lucide-react'
import { lazy, Suspense } from 'react'
import PageHead from '../components/PageHead'
import { shortName } from '../lib/insights'
import { useSim } from '../store/simStore'

const DemandWasteCard = lazy(() => import('../components/DemandWasteCard'))

function Fact({ Icon, label, value }: { Icon: typeof Droplets; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-panel-2 p-3">
      <Icon size={20} aria-hidden className="text-accent" />
      <div>
        <div className="text-xs font-semibold text-muted">{label}</div>
        <div className="text-lg font-extrabold">{value}</div>
      </div>
    </div>
  )
}

export default function Forecast() {
  const snap = useSim((s) => s.snapshot)
  const triggerEvent = useSim((s) => s.triggerEvent)
  if (!snap) return null
  const w = snap.weather
  const storm = snap.active_events.find((e) => e.type === 'rainstorm')

  return (
    <>
      <PageHead
        title="Demand forecast"
        lead="Expected sales per product for the next 24 simulated hours, adjusted for weather, foot traffic and the current price."
      >
        <button
          type="button"
          className="btn"
          disabled={snap.status === 'finished' || !!storm}
          onClick={() => triggerEvent('rainstorm')}
        >
          <CloudRain size={14} aria-hidden /> {storm ? 'Storm in progress' : 'Simulate a rainstorm'}
        </button>
      </PageHead>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <section aria-labelledby="wx-title" className="zone p-4">
          <h3 id="wx-title" className="h-card">
            Weather at the store
          </h3>
          <p className="text-sm text-muted">
            {w.location} · {w.source === 'live' ? 'live forecast' : 'recorded snapshot'}
            {w.short_forecast ? ` · ${w.short_forecast}` : ''}
          </p>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <Fact Icon={Thermometer} label="Temperature" value={w.temperature_f != null ? `${w.temperature_f}°F` : '—'} />
            <Fact Icon={Droplets} label="Humidity" value={`${w.relative_humidity_pct.toFixed(0)}%`} />
            <Fact Icon={CloudRain} label="Chance of rain" value={`${w.precip_probability_pct ?? 0}%`} />
            <Fact Icon={Footprints} label="Foot traffic" value={`×${w.traffic_mult.toFixed(2)}`} />
          </div>
          <p className={`mt-3 rounded-xl px-3 py-2 text-xs ${w.storm_active ? 'bg-agent-demand/10 text-agent-demand' : 'bg-panel-2 text-muted'}`}>
            {w.storm_active
              ? 'A storm is keeping shoppers home. ShelfSense lowered its forecast, so orders shrink and prices move.'
              : 'Humid air shortens fresh shelf life; rain cuts foot traffic. Both feed the forecast and the price formula.'}
          </p>
        </section>

        <Suspense fallback={<div className="zone h-[320px]" aria-busy />}>
          <DemandWasteCard esl={snap.esl} chart={snap.chart} />
        </Suspense>
      </div>

      <section aria-labelledby="fc-title" className="zone mt-5 p-4">
        <h3 id="fc-title" className="h-card">
          Stock vs expected sales
        </h3>
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs font-semibold text-muted">
              <th scope="col" className="py-2">Product</th>
              <th scope="col" className="py-2 text-right">On shelf</th>
              <th scope="col" className="py-2 text-right">
                <span className="sm:hidden">24 h demand</span>
                <span className="hidden sm:inline">Next 24 h demand</span>
              </th>
              <th scope="col" className="py-2 text-right">
                <span className="sm:hidden">Surplus</span>
                <span className="hidden sm:inline">Won’t sell in 24 h</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {snap.esl.map((e) => (
              <tr key={e.sku_id} className="border-b border-line/60 last:border-0">
                <td className="py-2 pr-2 font-semibold">{shortName(e.name)}</td>
                <td className="py-2 text-right">{e.on_hand}</td>
                <td className="py-2 text-right">{e.forecast_24h.toFixed(1)}</td>
                <td className={`py-2 text-right font-semibold ${e.surplus_risk_units ? 'text-warn' : 'text-muted'}`}>
                  {e.surplus_risk_units || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  )
}
