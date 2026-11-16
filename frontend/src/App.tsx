import { X } from 'lucide-react'
import { useEffect } from 'react'
import FormulaDrawer from './components/FormulaDrawer'
import WakingOverlay from './components/WakingOverlay'
import { api } from './lib/api'
import { connectSim } from './lib/ws'
import { useSim } from './store/simStore'
import AgentLog from './zones/AgentLog'
import EslMatrix from './zones/EslMatrix'
import ExecutionModules from './zones/ExecutionModules'
import SmartCamInspector from './zones/SmartCamInspector'
import TelemetryBar from './zones/TelemetryBar'

const WAKE_AFTER_MS = 3000
const HEALTH_RETRY_MS = 3000

/** Wait for /api/health (show the waking overlay if it takes > 3 s), then open the WebSocket. */
function useServerConnection() {
  const setConnection = useSim((s) => s.setConnection)
  const handleMessage = useSim((s) => s.handleMessage)

  useEffect(() => {
    let cancelled = false
    let disconnect: (() => void) | undefined
    const wake = window.setTimeout(() => !cancelled && setConnection('waking'), WAKE_AFTER_MS)

    const waitForHealth = async () => {
      while (!cancelled) {
        try {
          await api.health()
          return
        } catch {
          await new Promise((r) => window.setTimeout(r, HEALTH_RETRY_MS))
        }
      }
    }

    void waitForHealth().then(() => {
      window.clearTimeout(wake)
      if (cancelled) return
      disconnect = connectSim({
        onMessage: handleMessage,
        onOpen: () => setConnection('open'),
        onClose: () => setConnection('closed'),
      })
    })

    return () => {
      cancelled = true
      window.clearTimeout(wake)
      disconnect?.()
    }
  }, [setConnection, handleMessage])
}

function Notice() {
  const notice = useSim((s) => s.notice)
  const dismiss = useSim((s) => s.dismissNotice)
  const connection = useSim((s) => s.connection)
  const text = connection === 'closed' ? 'Connection lost — reconnecting…' : notice
  if (!text) return null
  return (
    <div
      role="alert"
      className="fixed bottom-4 left-1/2 z-40 flex -translate-x-1/2 items-center gap-3 rounded-md border border-warn/40 bg-panel-2 px-4 py-2 text-sm shadow-xl"
    >
      <span className="text-warn">{text}</span>
      {connection !== 'closed' && (
        <button type="button" className="btn-icon" aria-label="Dismiss" onClick={dismiss}>
          <X size={14} aria-hidden />
        </button>
      )}
    </div>
  )
}

export default function App() {
  useServerConnection()
  const connection = useSim((s) => s.connection)

  return (
    <div className="flex min-h-full flex-col gap-2 p-2 xl:grid xl:h-full xl:grid-cols-[340px_minmax(0,1fr)_380px] xl:grid-rows-[auto_minmax(0,1fr)_auto]">
      <div className="xl:col-span-3">
        <TelemetryBar />
      </div>
      <div className="xl:row-span-2 xl:min-h-0">
        <SmartCamInspector />
      </div>
      <div className="min-h-0 xl:overflow-y-auto">
        <EslMatrix />
      </div>
      <div className="h-[70vh] xl:row-span-2 xl:h-auto xl:min-h-0">
        <AgentLog />
      </div>
      <div>
        <ExecutionModules />
      </div>
      <FormulaDrawer />
      {connection === 'waking' && <WakingOverlay />}
      <Notice />
    </div>
  )
}
