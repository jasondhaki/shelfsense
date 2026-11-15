import EslCard from '../components/EslCard'
import { useSim } from '../store/simStore'

export default function EslMatrix() {
  const esl = useSim((s) => s.snapshot?.esl)
  const openFormula = useSim((s) => s.openFormula)

  return (
    <section aria-label="Electronic shelf labels" className="zone p-3">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-sm font-medium">Shelf labels — ShelfSense store</h2>
        <span className="text-[11px] text-muted">Select a label to see how its price was set</span>
      </div>
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        {esl?.map((e) => <EslCard key={e.sku_id} esl={e} onOpen={() => openFormula(e.sku_id)} />)}
      </div>
    </section>
  )
}
