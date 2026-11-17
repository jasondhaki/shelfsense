import { Network } from 'lucide-react'
import { useState } from 'react'
import ArchitectureModal from '../components/ArchitectureModal'
import PageHead from '../components/PageHead'
import { activeAgents, AGENT_CHIPS } from '../lib/insights'
import { useT, type Key } from '../lib/i18n'
import { useSim } from '../store/simStore'
import AgentLog from '../zones/AgentLog'
import SmartCamInspector from '../zones/SmartCamInspector'

const ROLE: Record<string, Key> = {
  DEMAND_AGENT: 'Forecasts hourly demand from sales history, weather and traffic.',
  PRICING_AGENT: 'Sets each label price from shelf life left and the sales gap.',
  VISION_AGENT: 'Grades shelf photos (Gemini) and shortens shelf life for damage.',
  PROCUREMENT_AGENT: 'Rebalances tomorrow’s orders to what will actually sell.',
  RAG_KNOWLEDGE_AGENT: 'Cites food-safety sources to explain each decision.',
}

export default function Agents() {
  const logs = useSim((s) => s.logs)
  const tick = useSim((s) => s.snapshot?.tick ?? 0)
  const [showArch, setShowArch] = useState(false)
  const t = useT()
  const active = activeAgents(logs, tick)

  return (
    <>
      <PageHead
        title={t('AI agents')}
        lead={t('Five agents share one message bus. They decide in plain arithmetic; the language model only reads photos and writes explanations.')}
      >
        <button type="button" className="btn" onClick={() => setShowArch(true)}>
          <Network size={14} aria-hidden /> {t('System architecture')}
        </button>
      </PageHead>
      <ArchitectureModal open={showArch} onClose={() => setShowArch(false)} />

      <ul className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {AGENT_CHIPS.map((c) => {
          const on = active.has(c.agent)
          const n = logs.filter((l) => l.agent === c.agent).length
          return (
            <li key={c.agent} className="zone p-3">
              <div className="flex items-center justify-between">
                <span className={`text-sm font-bold ${c.tone}`}>{t(c.label)}</span>
                <span className={`flex items-center gap-1 text-[11px] font-semibold ${on ? 'text-accent' : 'text-muted'}`}>
                  <span className={`h-2 w-2 rounded-full ${on ? 'bg-ok' : 'bg-baseline/50'}`} aria-hidden />
                  {t(on ? 'Active' : 'Idle')}
                </span>
              </div>
              <p className="mt-1 text-xs text-muted">{t(ROLE[c.agent])}</p>
              <p className="mt-2 text-xs font-semibold">{t('{n} log entries', { n })}</p>
            </li>
          )
        })}
      </ul>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
        <SmartCamInspector />
        <div className="h-[75vh] min-h-[480px]">
          <AgentLog />
        </div>
      </div>
    </>
  )
}
