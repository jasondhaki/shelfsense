import { Download } from 'lucide-react'
import InventoryTable from '../components/InventoryTable'
import PageHead from '../components/PageHead'
import { useT } from '../lib/i18n'
import { useSim } from '../store/simStore'

export default function Inventory() {
  const snap = useSim((s) => s.snapshot)
  const which = useSim((s) => s.eslStore)
  const setWhich = useSim((s) => s.setEslStore)
  const exportReport = useSim((s) => s.exportReport)
  const t = useT()
  if (!snap) return null
  const rows = which === 'A' ? snap.esl_a : snap.esl
  const units = rows.reduce((s, e) => s + e.on_hand, 0)

  return (
    <>
      <PageHead
        title={t('Inventory')}
        lead={t('{units} units across {lines} fresh lines. Select a product to see how its price was set.', { units, lines: rows.length })}
      >
        <div role="radiogroup" aria-label={t('Which store')} className="flex rounded-full border border-line bg-panel p-1">
          {(
            [
              ['B', 'ShelfSense store'],
              ['A', 'Baseline twin'],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="radio"
              aria-checked={which === id}
              onClick={() => setWhich(id)}
              className={`rounded-full px-3 py-1 text-xs font-semibold ${which === id ? 'bg-forest-800 text-white' : 'text-muted hover:text-text'}`}
            >
              {t(label)}
            </button>
          ))}
        </div>
        <button type="button" className="btn" onClick={() => exportReport()}>
          <Download size={14} aria-hidden /> {t('Export CSV')}
        </button>
      </PageHead>
      <InventoryTable rows={rows} detailed />
      <p className="mt-3 text-xs text-muted">
        {t('Freshness = shelf life left on the oldest batch ÷ the item’s nominal shelf life (USDA FoodKeeper).')}{' '}
        {which === 'A'
          ? t('The baseline store only knows the printed date, so its countdown ignores heat or damage.')
          : t('ShelfSense adjusts it for humidity and vision scans.')}
      </p>
    </>
  )
}
