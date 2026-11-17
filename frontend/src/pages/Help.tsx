import PageHead from '../components/PageHead'
import { useT, type Key } from '../lib/i18n'

const STEPS: [Key, Key][] = [
  ['Press play', 'The week runs at one simulated hour per second; fast-forward runs a simulated day per second. Both stores see identical shoppers.'],
  ['Watch the dashboard', 'Waste reduction compares this store with its baseline twin, which only knows printed dates and marks down 50% on the last day.'],
  ['Scan the shelf', 'The freshness scanner grades a camera frame. Damage shortens shelf life, and the label reprices on the next hour.'],
  ['Test a disruption', 'A rainstorm cuts foot traffic; a cold-chain delay makes the next delivery arrive with less shelf life. Orders and prices respond.'],
  ['Ask why', 'Select any product to see the exact price formula, with assumed values labelled.'],
]

export default function Help() {
  const t = useT()
  return (
    <>
      <PageHead title={t('Help')} lead={t('How to run a demo, and what is real versus simulated.')} />
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <section aria-labelledby="how-title" className="zone p-4">
          <h3 id="how-title" className="h-card">
            {t('Run a demo in five steps')}
          </h3>
          <ol className="mt-3 space-y-3">
            {STEPS.map(([title, d], i) => (
              <li key={title} className="flex gap-3">
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-mint text-sm font-bold text-accent">{i + 1}</span>
                <div>
                  <div className="text-sm font-bold">{t(title)}</div>
                  <p className="text-sm text-muted">{t(d)}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>
        <section aria-labelledby="honest-title" className="zone p-4">
          <h3 id="honest-title" className="h-card">
            {t('What’s real, what’s simulated')}
          </h3>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-muted">
            <li>{t('Shoppers, sales and waste are simulated from public data (Favorita sales shape, FoodKeeper shelf life, FAO waste rates).')}</li>
            <li>{t('Price elasticities (−1.4 to −2.2) and the share of markdown sales borrowed from later hours (0.5) are assumptions.')}</li>
            <li>{t('The vision model reads photos; it never sets a price. Prices, shelf life and orders are plain arithmetic.')}</li>
            <li>{t('The public demo uses cached vision results for the preset frames, so it works without an API key.')}</li>
            <li>{t('The baseline store is calibrated to land near FAO retail waste rates, not observed in a real shop.')}</li>
          </ul>
        </section>
      </div>
    </>
  )
}
