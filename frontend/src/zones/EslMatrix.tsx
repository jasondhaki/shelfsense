import { Download } from 'lucide-react'
import EslCard from '../components/EslCard'
import { useSim } from '../store/simStore'

const STORES = [
  { id: 'B', label: 'ShelfSense store' },
  { id: 'A', label: 'Baseline store' },
] as const

export default function EslMatrix() {
  const which = useSim((s) => s.eslStore)
  const setWhich = useSim((s) => s.setEslStore)
  const esl = useSim((s) => (which === 'A' ? s.snapshot?.esl_a : s.snapshot?.esl))
  const openFormula = useSim((s) => s.openFormula)
  const exportReport = useSim((s) => s.exportReport)

  return (
    <section aria-label="Electronic shelf labels" className="zone p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-medium">Shelf labels</h2>
          <div role="radiogroup" aria-label="Which store" className="flex rounded-md border border-line p-0.5">
            {STORES.map((s) => (
              <button
                key={s.id}
                type="button"
                role="radio"
                aria-checked={which === s.id}
                onClick={() => setWhich(s.id)}
                className={`rounded px-2 py-0.5 text-[11px] font-medium ${which === s.id ? 'bg-panel-2 text-text' : 'text-muted hover:text-text'}`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-muted">
            {which === 'B'
              ? 'Select a label to see how its price was set'
              : 'Printed-date pricing: 50% off on the last labelled day'}
          </span>
          <button type="button" className="btn" onClick={() => exportReport()}>
            <Download size={13} aria-hidden />
            Export CSV
          </button>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {esl?.map((e) => (
          <EslCard
            key={e.sku_id}
            esl={e}
            baseline={which === 'A'}
            onOpen={which === 'B' ? () => openFormula(e.sku_id) : undefined}
          />
        ))}
      </div>
    </section>
  )
}
