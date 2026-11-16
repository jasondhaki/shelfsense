import BundleCard from '../components/BundleCard'
import PageHead from '../components/PageHead'
import { useSim } from '../store/simStore'
import EslMatrix from '../zones/EslMatrix'

export default function Pricing() {
  const bundles = useSim((s) => s.snapshot?.bundles ?? [])
  const newest = [...bundles].reverse().slice(0, 12)
  const listed = bundles.filter((b) => b.status === 'listed').length
  return (
    <>
      <PageHead
        title="Pricing & discounts"
        lead="Electronic shelf labels reprice every hour from shelf life left and expected sales. Elasticities are assumptions, labelled in each formula."
      />
      <EslMatrix />
      <section aria-labelledby="box-title" className="zone mt-5 p-4">
        <div className="flex items-center justify-between">
          <h3 id="box-title" className="h-card">
            Flash surplus boxes
          </h3>
          <span className="text-xs font-semibold text-muted">
            {listed} listed now · {bundles.length} this week{bundles.length > 12 ? ' (newest 12 shown)' : ''}
          </span>
        </div>
        {newest.length === 0 ? (
          <p className="mt-2 text-sm text-muted">
            No boxes yet. A box is made when an item drops below 8 hours of shelf life and price cuts alone can’t
            clear it.
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
