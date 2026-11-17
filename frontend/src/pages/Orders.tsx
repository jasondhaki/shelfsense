import ColdChainPopover from '../components/ColdChainPopover'
import PageHead from '../components/PageHead'
import PoTable from '../components/PoTable'
import { rich, useT } from '../lib/i18n'
import { useSim } from '../store/simStore'

export default function Orders() {
  const snap = useSim((s) => s.snapshot)
  const poRegular = useSim((s) => s.poRegular)
  const triggerEvent = useSim((s) => s.triggerEvent)
  const t = useT()
  if (!snap) return null
  const saved = snap.po_table.reduce((s, r) => s + r.waste_prevention_kg, 0)

  return (
    <>
      <PageHead
        title={t('Purchase orders')}
        lead={t('Tomorrow’s orders are planned at 21:00, or straight away when the weather changes. The baseline twin reorders a fixed par level.')}
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
              {rich(t('This round avoids an estimated {kg} of waste compared with the baseline order.'), {
                kg: <strong className="text-accent">{saved.toFixed(1)} kg</strong>,
              })}
            </>
          ) : (
            <>
              {rich(t('This round orders {kg} more than the baseline, because expected sales are above the baseline’s fixed par level.'), {
                kg: <strong>{Math.abs(saved).toFixed(1)} kg</strong>,
              })}
            </>
          )}
        </p>
      )}
      <section aria-label={t('Purchase orders')} className="zone overflow-x-auto">
        <PoTable rows={snap.po_table} regular={poRegular} />
      </section>
    </>
  )
}
