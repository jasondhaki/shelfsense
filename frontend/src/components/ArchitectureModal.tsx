import { ChevronRight, Circle, CircleDot, Minus, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import { useSim } from '../store/simStore'
import type { ArchNode, Architecture } from '../types/contracts'

const LAYERS: { id: ArchNode['layer']; label: string }[] = [
  { id: 'source', label: 'Data sources' },
  { id: 'knowledge', label: 'Seed data & RAG' },
  { id: 'agent', label: 'Agents' },
  { id: 'core', label: 'Orchestrator' },
  { id: 'output', label: 'Store outputs' },
]

const STATUS = {
  live: { label: 'Live', cls: 'text-ok', Icon: CircleDot },
  fallback: { label: 'Offline fallback', cls: 'text-muted', Icon: Circle },
  static: { label: 'Built from source data', cls: 'text-baseline', Icon: Minus },
} as const

function Node({ n, active, feeds }: { n: ArchNode; active: boolean; feeds: string[] }) {
  const s = STATUS[n.status]
  return (
    <li
      className={`rounded-md border bg-panel-2 p-2 transition-colors ${active ? 'border-accent motion-safe:animate-pulse' : 'border-line'}`}
      aria-label={`${n.label}: ${s.label}. ${n.detail}${active ? '. Active this hour' : ''}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium">{n.label}</span>
        <span className={`flex items-center gap-1 text-[10px] ${s.cls}`}>
          <s.Icon size={10} aria-hidden />
          {s.label}
        </span>
      </div>
      <div className="mt-0.5 text-[11px] text-muted">{n.detail}</div>
      {feeds.length > 0 && (
        <div className="mt-1 truncate text-[10px] text-muted/70">→ {feeds.join(', ')}</div>
      )}
    </li>
  )
}

export default function ArchitectureModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const [arch, setArch] = useState<Architecture | null>(null)
  const [error, setError] = useState<string | null>(null)
  const logs = useSim((s) => s.logs)
  const tick = useSim((s) => s.snapshot?.tick ?? 0)

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) {
      d.showModal()
      api
        .architecture()
        .then((a) => {
          setArch(a)
          setError(null)
        })
        .catch(() => setError('Couldn’t load the live status. The diagram below may be out of date.'))
    } else if (!open && d.open) d.close()
  }, [open])

  // agents that wrote a log line during the latest tick pulse
  const active = new Set(logs.filter((l) => l.tick === tick - 1).map((l) => l.agent))
  const label = (id: string) => arch?.nodes.find((n) => n.id === id)?.label ?? id

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-labelledby="arch-title"
      className="w-[min(1100px,calc(100vw-2rem))] rounded-lg border border-line bg-panel p-0 text-text backdrop:bg-bg/80"
    >
      <div className="flex items-start justify-between border-b border-line p-4">
        <div>
          <h2 id="arch-title" className="text-base font-semibold">
            System architecture
          </h2>
          <p className="text-xs text-muted">
            Live status of every part. Agents light up when they act on the current hour.
          </p>
        </div>
        <button type="button" className="btn-icon" aria-label="Close system architecture" onClick={onClose}>
          <X size={16} aria-hidden />
        </button>
      </div>
      <div className="p-4">
        {error && <p className="mb-3 text-xs text-warn">{error}</p>}
        <div className="grid grid-cols-1 gap-2 md:grid-cols-[repeat(5,minmax(0,1fr))]">
          {LAYERS.map((layer, i) => (
            <section key={layer.id} aria-label={layer.label} className="relative">
              <h3 className="mb-1.5 text-[11px] text-muted">{layer.label}</h3>
              <ul className="space-y-1.5">
                {arch?.nodes
                  .filter((n) => n.layer === layer.id)
                  .map((n) => (
                    <Node
                      key={n.id}
                      n={n}
                      active={n.agent !== null && active.has(n.agent)}
                      feeds={arch.edges.filter((e) => e.source === n.id).map((e) => label(e.target))}
                    />
                  ))}
              </ul>
              {i < LAYERS.length - 1 && (
                <ChevronRight
                  size={16}
                  className="absolute -right-3 top-1/2 hidden text-muted md:block"
                  aria-hidden
                />
              )}
            </section>
          ))}
        </div>
        <p className="mt-4 text-[11px] text-muted">
          Prices, shelf life and orders are computed by a deterministic engine from these inputs. The
          vision model only extracts what it sees, and retrieved text only explains decisions; neither
          sets a number. Elasticities are assumptions.
        </p>
      </div>
    </dialog>
  )
}
