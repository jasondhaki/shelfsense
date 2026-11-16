import ColdChainPopover from '../components/ColdChainPopover'
import PageHead from '../components/PageHead'
import PoTable from '../components/PoTable'
import { useSim } from '../store/simStore'

export default function Orders() {
  const snap = useSim((s) => s.snapshot)
  const poRegular = useSim((s) => s.poRegular)
  const triggerEvent = useSim((s) => s.triggerEvent)
  if (!snap) return null
  const saved = snap.po_table.reduce((s, r) => s + r.waste_prevention_kg, 0)

  return (
    <>
      <PageHead
        title="Purchase orders"
        lead="Tomorrow’s orders are planned at 21:00, or straight away when the weather changes. The baseline twin reorders a fixed par level."
      >
        <ColdChainPopover
          skus={snap.esl}
          pending={snap.active_events.some((e) => e.type === 'cold_chain_delay')}
          disabled={snap.status === 'finished'}
          onTrigger={(skus, immediate) => triggerEvent('cold_chain_delay', { skus, immediate })}
        />
      </PageHead>
      {snap.po_table.length > 0 && (
        <p className="mb-3 text-sm">
          {saved >= 0 ? (
            <>
              This round avoids an estimated <strong className="text-accent">{saved.toFixed(1)} kg</strong> of waste
              compared with the baseline order.
            </>
          ) : (
            <>
              This round orders <strong>{Math.abs(saved).toFixed(1)} kg</strong> more than the baseline, because
              expected sales are above the baseline’s fixed par level.
            </>
          )}
        </p>
      )}
      <section aria-label="Purchase orders" className="zone overflow-x-auto">
        <PoTable rows={snap.po_table} regular={poRegular} />
      </section>
    </>
  )
}
