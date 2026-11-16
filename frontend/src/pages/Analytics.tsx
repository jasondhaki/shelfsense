import { Download } from 'lucide-react'
import { lazy, Suspense } from 'react'
import PageHead from '../components/PageHead'
import { usd } from '../lib/format'
import { useSim } from '../store/simStore'

const WasteChart = lazy(() => import('../components/WasteChart'))

export default function Analytics() {
  const snap = useSim((s) => s.snapshot)
  const exportReport = useSim((s) => s.exportReport)
  if (!snap) return null
  const k = snap.kpis
  const last = snap.chart[snap.chart.length - 1]

  const rows: [string, string, string][] = [
    ['Food wasted', `${k.waste_kg_a.toFixed(1)} kg`, `${k.waste_kg_b.toFixed(1)} kg`],
    ['Revenue', last ? usd(last.revenue_a) : '—', last ? usd(last.revenue_b) : '—'],
  ]

  return (
    <>
      <PageHead
        title="Analytics"
        lead="The twin-store comparison: identical shoppers every hour, one store run by printed dates, one by ShelfSense."
      >
        <button type="button" className="btn" onClick={() => exportReport()}>
          <Download size={14} aria-hidden /> Export CSV
        </button>
      </PageHead>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <section aria-label="Food wasted so far" className="zone h-[380px] p-4">
          <Suspense fallback={<p className="p-4 text-sm text-muted">Loading chart…</p>}>
            <WasteChart data={snap.chart} />
          </Suspense>
        </section>

        <section aria-labelledby="cmp-title" className="zone p-4">
          <h3 id="cmp-title" className="h-card">
            Baseline vs ShelfSense
          </h3>
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs font-semibold text-muted">
                <th scope="col" className="py-2" />
                <th scope="col" className="py-2 text-right">Baseline</th>
                <th scope="col" className="py-2 text-right">ShelfSense</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([label, a, b]) => (
                <tr key={label} className="border-b border-line/60">
                  <th scope="row" className="py-2 text-left font-semibold">{label}</th>
                  <td className="py-2 text-right">{a}</td>
                  <td className="py-2 text-right font-bold">{b}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="mt-4 grid grid-cols-2 gap-3">
            {(
              [
                ['Waste reduction', k.waste_reduction_pct === null ? '—' : `${k.waste_reduction_pct.toFixed(1)}%`],
                ['Food diverted', `${k.food_diverted_kg.toFixed(1)} kg`],
                ['CO₂e avoided', `${k.co2e_avoided_kg.toFixed(1)} kg`],
                ['Margin recovered', usd(k.net_margin_recovered_usd)],
              ] as const
            ).map(([dt, dd]) => (
              <div key={dt} className="rounded-xl bg-panel-2 p-3">
                <dt className="text-xs font-semibold text-muted">{dt}</dt>
                <dd className="text-lg font-extrabold">{dd}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs text-muted">
            Across seeds 1–20 with no disruptions the reduction averages 57.8% ± 8.5. Elasticities and the
            pull-forward share are assumptions, so treat these as simulated results.
          </p>
        </section>
      </div>
    </>
  )
}
