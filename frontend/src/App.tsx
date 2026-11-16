import { X } from 'lucide-react'
import { useEffect } from 'react'
import FormulaDrawer from './components/FormulaDrawer'
import WakingOverlay from './components/WakingOverlay'
import MobileNav from './layout/MobileNav'
import Sidebar from './layout/Sidebar'
import SimBar from './layout/SimBar'
import TopBar from './layout/TopBar'
import { api } from './lib/api'
import { connectSim } from './lib/ws'
import Agents from './pages/Agents'
import Analytics from './pages/Analytics'
import Dashboard from './pages/Dashboard'
import DataIngestion from './pages/DataIngestion'
import Forecast from './pages/Forecast'
import Help from './pages/Help'
import Inventory from './pages/Inventory'
import Orders from './pages/Orders'
import Pricing from './pages/Pricing'
import Settings from './pages/Settings'
import { useSim, type Page } from './store/simStore'

const PAGES: Record<Page, () => JSX.Element | null> = {
  dashboard: Dashboard,
  inventory: Inventory,
  forecast: Forecast,
  pricing: Pricing,
  agents: Agents,
  orders: Orders,
  analytics: Analytics,
  data: DataIngestion,
  settings: Settings,
  help: Help,
}

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
      className="fixed bottom-4 left-1/2 z-40 flex -translate-x-1/2 items-center gap-3 rounded-full border border-warn/40 bg-panel px-4 py-2 text-sm font-semibold shadow-card"
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
  const page = useSim((s) => s.page)
  const syncPage = useSim((s) => s.syncPage)

  useEffect(() => {
    window.addEventListener('hashchange', syncPage)
    return () => window.removeEventListener('hashchange', syncPage)
  }, [syncPage])

  const Current = PAGES[page]

  return (
    <div className="flex min-h-full">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <MobileNav />
        <main className="mx-auto max-w-[1680px] space-y-5 px-4 py-5 sm:px-6 lg:px-8">
          <TopBar />
          <SimBar />
          <Current />
        </main>
      </div>
      <FormulaDrawer />
      {connection === 'waking' && <WakingOverlay />}
      <Notice />
    </div>
  )
}
