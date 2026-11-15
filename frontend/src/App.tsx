import { useEffect, useState } from 'react'

type Health = 'checking' | 'ok' | 'down'

function Zone({ title, className = '' }: { title: string; className?: string }) {
  return (
    <section className={`rounded-lg border border-line bg-panel p-3 ${className}`}>
      <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">{title}</h2>
    </section>
  )
}

export default function App() {
  const [health, setHealth] = useState<Health>('checking')

  useEffect(() => {
    fetch('/api/health')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((b: { status: string }) => setHealth(b.status === 'ok' ? 'ok' : 'down'))
      .catch(() => setHealth('down'))
  }, [])

  const dot = { checking: 'bg-warn', ok: 'bg-ok', down: 'bg-crit' }[health]

  return (
    <div className="grid h-full min-w-[1280px] grid-cols-[340px_1fr_380px] grid-rows-[auto_1fr_auto] gap-2 p-2">
      <header className="col-span-3 flex items-center justify-between rounded-lg border border-line bg-panel px-4 py-3">
        <div>
          <div className="text-lg font-bold tracking-tight">ShelfSense</div>
          <div className="text-xs text-muted">a FoodSphere AI system</div>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs" aria-live="polite">
          <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden />
          backend: {health}
        </div>
      </header>
      <Zone title="Zone B · Smart-Cam Inspector" className="row-span-2" />
      <Zone title="Zone C · ESL Matrix" />
      <Zone title="Zone E · Agent Reasoning Log" className="row-span-2" />
      <Zone title="Zone D · Procurement / Bundles" className="min-h-[240px]" />
    </div>
  )
}
