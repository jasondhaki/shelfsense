import { ExternalLink, Network } from 'lucide-react'
import { useEffect, useState } from 'react'
import ArchitectureModal from '../components/ArchitectureModal'
import PageHead from '../components/PageHead'
import { api } from '../lib/api'
import type { ArchNode } from '../types/contracts'

const SOURCES: { name: string; use: string; url: string }[] = [
  { name: 'USDA FoodKeeper', use: 'Nominal shelf life per product', url: 'https://catalog.data.gov/dataset/fsis-foodkeeper-data' },
  { name: 'Open Food Facts', use: 'Nutri-Score, packaging, product facts', url: 'https://world.openfoodfacts.org/' },
  { name: 'Favorita (Kaggle)', use: 'Day-of-week and hourly sales shape, promo lift', url: 'https://www.kaggle.com/competitions/favorita-grocery-sales-forecasting/data' },
  { name: 'NOAA weather.gov / Open-Meteo', use: 'Humidity and rain for shelf life and traffic', url: 'https://api.weather.gov' },
  { name: 'FAO', use: 'Retail waste rates the baseline is calibrated to', url: 'https://www.fao.org/4/mb060e/mb060e.pdf' },
  { name: 'Poore & Nemecek / OWID', use: 'CO₂e per kg by food category', url: 'https://ourworldindata.org/grapher/ghg-per-kg-poore' },
  { name: 'USDA AMS / UC Davis', use: 'Ethylene producers and sensitive items for surplus boxes', url: 'https://www.ams.usda.gov/sites/default/files/media/2023Technical_Report_Ethylene_Handling.pdf' },
  { name: 'Unsplash', use: 'Shelf-camera frames and product photos', url: 'https://unsplash.com/license' },
]

const STATUS: Record<ArchNode['status'], { label: string; cls: string }> = {
  live: { label: 'Live', cls: 'bg-mint text-accent' },
  fallback: { label: 'Offline fallback', cls: 'bg-warn/10 text-warn' },
  static: { label: 'Recorded', cls: 'bg-panel-2 text-muted' },
}

export default function DataIngestion() {
  const [nodes, setNodes] = useState<ArchNode[] | null>(null)
  const [error, setError] = useState(false)
  const [showArch, setShowArch] = useState(false)

  useEffect(() => {
    api
      .architecture()
      .then((a) => setNodes(a.nodes.filter((n) => n.layer === 'source' || n.layer === 'knowledge')))
      .catch(() => setError(true))
  }, [])

  return (
    <>
      <PageHead
        title="Data ingestion"
        lead="Every input is a free public dataset. Each external call has an offline fallback, so the demo runs with no keys and no internet."
      >
        <button type="button" className="btn" onClick={() => setShowArch(true)}>
          <Network size={14} aria-hidden /> System architecture
        </button>
      </PageHead>
      <ArchitectureModal open={showArch} onClose={() => setShowArch(false)} />

      <section aria-labelledby="feeds-title" className="zone p-4">
        <h3 id="feeds-title" className="h-card">
          Feeds right now
        </h3>
        {error && <p className="mt-2 text-sm text-warn">Couldn’t load the live status from the server.</p>}
        <ul className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {(nodes ?? []).map((n) => (
            <li key={n.id} className="rounded-xl border border-line p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="font-bold">{n.label}</span>
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${STATUS[n.status].cls}`}>{STATUS[n.status].label}</span>
              </div>
              <p className="mt-1 text-xs text-muted">{n.detail}</p>
            </li>
          ))}
          {!nodes && !error && <li className="text-sm text-muted">Loading…</li>}
        </ul>
      </section>

      <section aria-labelledby="src-title" className="zone mt-5 p-4">
        <h3 id="src-title" className="h-card">
          Sources and credits
        </h3>
        <ul className="mt-2 divide-y divide-line/70">
          {SOURCES.map((s) => (
            <li key={s.name} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
              <div>
                <div className="text-sm font-bold">{s.name}</div>
                <div className="text-xs text-muted">{s.use}</div>
              </div>
              <a href={s.url} target="_blank" rel="noreferrer" className="link">
                Source <ExternalLink size={12} aria-hidden />
                <span className="sr-only">(opens in a new tab)</span>
              </a>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}
