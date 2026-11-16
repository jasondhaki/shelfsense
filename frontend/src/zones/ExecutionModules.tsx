import BundleCard from '../components/BundleCard'
import PoTable from '../components/PoTable'
import WasteChart from '../components/WasteChart'
import { useSim } from '../store/simStore'

const TABS = [
  { id: 'procurement', label: 'Purchase orders' },
  { id: 'bundles', label: 'Flash surplus boxes' },
] as const

export default function ExecutionModules() {
  const snap = useSim((s) => s.snapshot)
  const tab = useSim((s) => s.activeTab)
  const setTab = useSim((s) => s.setTab)
  const poRegular = useSim((s) => s.poRegular)

  const bundles = [...(snap?.bundles ?? [])].reverse() // newest first
  const listed = bundles.filter((b) => b.status === 'listed').length

  return (
    <section
      aria-label="Purchase orders, surplus boxes and waste chart"
      className="zone grid min-h-[280px] grid-cols-1 gap-3 p-3 lg:h-[300px] lg:grid-cols-[minmax(0,1fr)_minmax(0,0.75fr)]"
    >
      <div className="flex min-h-0 flex-col">
        <div role="tablist" aria-label="Execution modules" className="mb-2 flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              id={`tab-${t.id}`}
              aria-selected={tab === t.id}
              aria-controls={`panel-${t.id}`}
              onClick={() => setTab(t.id)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium ${
                tab === t.id ? 'bg-panel-2 text-text' : 'text-muted hover:text-text'
              }`}
            >
              {t.label}
              {t.id === 'bundles' && listed > 0 && (
                <span className="ml-1.5 rounded-full bg-accent/20 px-1.5 font-mono text-[10px] text-accent">
                  {listed}
                </span>
              )}
            </button>
          ))}
        </div>
        <div
          role="tabpanel"
          id={`panel-${tab}`}
          aria-labelledby={`tab-${tab}`}
          className="min-h-0 flex-1 overflow-auto rounded-md border border-line"
        >
          {tab === 'procurement' ? (
            <PoTable rows={snap?.po_table ?? []} regular={poRegular} />
          ) : bundles.length === 0 ? (
            <p className="p-4 text-sm text-muted">
              No boxes yet. Boxes appear when an item drops below 8 hours of shelf life and price
              cuts alone can’t clear it.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-2 p-2 sm:grid-cols-2 xl:grid-cols-3">
              {bundles.map((b) => (
                <BundleCard key={b.bundle_id} b={b} />
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="min-h-[220px] lg:min-h-0">
        <WasteChart data={snap?.chart ?? []} />
      </div>
    </section>
  )
}
