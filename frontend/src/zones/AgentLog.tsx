import { ArrowDown } from 'lucide-react'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { AGENTS, useSim } from '../store/simStore'
import type { AgentName, LogEntry } from '../types/contracts'

const TAG: Record<AgentName, { short: string; cls: string }> = {
  VISION_AGENT: { short: 'VISION', cls: 'text-agent-vision' },
  RAG_KNOWLEDGE_AGENT: { short: 'RAG', cls: 'text-agent-rag' },
  DEMAND_AGENT: { short: 'DEMAND', cls: 'text-agent-demand' },
  PRICING_AGENT: { short: 'PRICING', cls: 'text-agent-pricing' },
  PROCUREMENT_AGENT: { short: 'PROCUREMENT', cls: 'text-agent-procurement' },
  SYSTEM: { short: 'SYSTEM', cls: 'text-muted' },
}

function Line({ e }: { e: LogEntry }) {
  const tag = TAG[e.agent]
  const head = (
    <>
      <span className="text-muted">[{e.sim_time}]</span>{' '}
      <span className={tag.cls}>[{e.agent}]</span>{' '}
      <span className={e.level === 'warn' ? 'text-warn' : 'text-text'}>
        {e.level === 'warn' && '⚠ '}
        {e.message}
      </span>
    </>
  )
  if (!e.data) return <div className="px-3 py-0.5">{head}</div>
  return (
    <details className="group px-3 py-0.5 open:bg-panel-2">
      <summary className="cursor-pointer list-none marker:hidden">{head}</summary>
      <pre className="mt-1 max-h-48 overflow-auto rounded bg-bg p-2 text-[11px] text-muted">
        {JSON.stringify(e.data, null, 2)}
      </pre>
    </details>
  )
}

export default function AgentLog() {
  const logs = useSim((s) => s.logs)
  const filter = useSim((s) => s.logFilter)
  const toggle = useSim((s) => s.toggleAgent)
  const box = useRef<HTMLDivElement>(null)
  const [pinned, setPinned] = useState(true)

  const shown = logs.filter((l) => filter.has(l.agent))

  useLayoutEffect(() => {
    if (pinned && box.current) box.current.scrollTop = box.current.scrollHeight
  }, [shown.length, pinned])

  useEffect(() => {
    const el = box.current
    if (!el) return
    const onScroll = () => setPinned(el.scrollHeight - el.scrollTop - el.clientHeight < 24)
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <section aria-label="Agent reasoning log" className="zone relative flex min-h-0 flex-col">
      <div className="border-b border-line p-3">
        <h2 className="mb-2 text-sm font-medium">Agent reasoning log</h2>
        <div className="flex flex-wrap gap-1" role="group" aria-label="Show agents">
          {AGENTS.map((a) => (
            <button
              key={a}
              type="button"
              aria-pressed={filter.has(a)}
              onClick={() => toggle(a)}
              className={`rounded-full border px-2 py-0.5 font-mono text-[10px] ${
                filter.has(a) ? `border-line bg-panel-2 ${TAG[a].cls}` : 'border-line/50 text-muted/50 line-through'
              }`}
            >
              {TAG[a].short}
            </button>
          ))}
        </div>
      </div>
      <div
        ref={box}
        className="min-h-0 flex-1 overflow-y-auto py-2 font-mono text-[11.5px] leading-relaxed"
        aria-live="off"
      >
        {shown.length === 0 ? (
          <p className="px-3 text-muted">Press play to start the week. Agent decisions appear here.</p>
        ) : (
          shown.map((e, i) => <Line key={`${e.tick}-${i}`} e={e} />)
        )}
      </div>
      {!pinned && (
        <button
          type="button"
          onClick={() => setPinned(true)}
          className="btn absolute bottom-3 left-1/2 -translate-x-1/2 shadow-lg"
        >
          <ArrowDown size={14} aria-hidden /> Jump to latest
        </button>
      )}
    </section>
  )
}
