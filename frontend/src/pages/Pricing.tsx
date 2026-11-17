import BundleCard from '../components/BundleCard'
import PageHead from '../components/PageHead'
import { useT } from '../lib/i18n'
import { useSim } from '../store/simStore'
import EslMatrix from '../zones/EslMatrix'

export default function Pricing() {
  const bundles = useSim((s) => s.snapshot?.bundles ?? [])
  const newest = [...bundles].reverse().slice(0, 12)
  const listed = bundles.filter((b) => b.status === 'listed').length
  const t = useT()
  return (
    <>
      <PageHead
        title={t('Pricing & discounts')}
        lead={t('Electronic shelf labels reprice every hour from shelf life left and expected sales. Elasticities are assumptions, labelled in each formula.')}
      />
      <EslMatrix />
      <section aria-labelledby="box-title" className="zone mt-5 p-4">
        <div className="flex items-center justify-between">
          <h3 id="box-title" className="h-card">
            {t('Flash surplus boxes')}
          </h3>
          <span className="text-xs font-semibold text-muted">
            {t('{n} listed now · {w} this week', { n: listed, w: bundles.length })}{bundles.length > 12 ? ` ${t('(newest 12 shown)')}` : ''}
          </span>
        </div>
        {newest.length === 0 ? (
          <p className="mt-2 text-sm text-muted">
            {t('No boxes yet. A box is made when an item drops below 8 hours of shelf life and price cuts alone can’t clear it.')}
          </p>
        ) : (
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {newest.map((b) => (
              <BundleCard key={b.bundle_id} b={b} />
            ))}
          </div>
        )}
      </section>
    </>
  )
}
