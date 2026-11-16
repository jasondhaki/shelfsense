import { create } from 'zustand'
import { api, ApiFailure } from '../lib/api'
import { rejectReason, shrinkForVision } from '../lib/image'
import type {
  AgentName,
  PoRow,
  ControlAction,
  EventType,
  FormulaBreakdown,
  FrameId,
  VisionScanResult,
  LogEntry,
  ServerMessage,
  SimSnapshot,
  TickMessage,
} from '../types/contracts'

const LOG_LIMIT = 500

export const AGENTS: AgentName[] = [
  'VISION_AGENT',
  'RAG_KNOWLEDGE_AGENT',
  'DEMAND_AGENT',
  'PRICING_AGENT',
  'PROCUREMENT_AGENT',
  'SYSTEM',
]

export type Connection = 'connecting' | 'waking' | 'open' | 'closed'

export const FRAMES: { id: FrameId; label: string; src: string }[] = [
  { id: 'frame1', label: 'Day 1 morning', src: '/frames/frame1.jpg' },
  { id: 'frame2', label: 'Day 3 afternoon', src: '/frames/frame2.jpg' },
  { id: 'frame3', label: 'Thermal anomaly', src: '/frames/frame3.jpg' },
]

interface VisionState {
  frameId: FrameId | 'custom'
  imageUrl: string
  upload: File | null
  result: VisionScanResult | null
  scanning: boolean
  error?: string
}

interface SimStore {
  connection: Connection
  snapshot: SimSnapshot | null
  logs: LogEntry[]
  logFilter: Set<AgentName>
  selectedSku: string | null
  formula: FormulaBreakdown | null
  activeTab: 'procurement' | 'bundles'
  eslStore: 'B' | 'A'
  notice: string | null
  vision: VisionState
  /** ShelfSense orders from the last regular (non-weather) PO run, to show what a weather recompute moved. */
  poRegular: Record<string, number>
  setConnection(c: Connection): void
  handleMessage(m: ServerMessage): void
  applyHello(s: SimSnapshot): void
  applyTick(m: TickMessage): void
  toggleAgent(a: AgentName): void
  control(action: ControlAction, extra?: { scenario?: 'none' | 'demo' }): Promise<void>
  triggerEvent(type: EventType, payload?: Record<string, unknown>): Promise<void>
  openFormula(skuId: string): Promise<void>
  closeFormula(): void
  setTab(t: 'procurement' | 'bundles'): void
  setEslStore(s: 'B' | 'A'): void
  exportReport(): Promise<void>
  dismissNotice(): void
  selectFrame(id: FrameId): void
  selectUpload(f: File): void
  scan(): Promise<void>
}

const trim = (logs: LogEntry[]) => (logs.length > LOG_LIMIT ? logs.slice(-LOG_LIMIT) : logs)

const regularOrders = (rows: PoRow[], prev: Record<string, number>) =>
  rows.length && rows.every((r) => r.reason === null)
    ? Object.fromEntries(rows.map((r) => [r.sku_id, r.ai_order]))
    : prev

const failure = (e: unknown) =>
  e instanceof ApiFailure ? e.message : 'Something went wrong talking to the server.'

export const useSim = create<SimStore>()((set, get) => ({
  connection: 'connecting',
  snapshot: null,
  logs: [],
  logFilter: new Set(AGENTS),
  selectedSku: null,
  formula: null,
  activeTab: 'procurement',
  eslStore: 'B',
  notice: null,
  poRegular: {},
  vision: { frameId: 'frame1', imageUrl: FRAMES[0].src, upload: null, result: null, scanning: false },

  setConnection: (connection) => set({ connection }),

  handleMessage: (m) => {
    switch (m.type) {
      case 'hello':
        get().applyHello(m.snapshot)
        break
      case 'tick':
        get().applyTick(m)
        break
      case 'status':
        set((s) => (s.snapshot ? { snapshot: { ...s.snapshot, status: m.status, speed: m.speed } } : {}))
        break
      default:
        break // event_applied and pong: the tick message carries the visible effects
    }
  },

  applyHello: (snapshot) =>
    set({
      snapshot,
      logs: trim(snapshot.logs),
      poRegular: regularOrders(snapshot.po_table, {}),
    }),

  applyTick: ({ tick, delta, logs }) =>
    set((s) => {
      if (!s.snapshot) return {}
      const snap = s.snapshot
      return {
        snapshot: {
          ...snap,
          tick,
          kpis: delta.kpis,
          esl: delta.esl,
          esl_a: delta.esl_a,
          po_table: delta.po_table ?? snap.po_table,
          bundles: delta.bundles ?? snap.bundles,
          weather: delta.weather ?? snap.weather,
          active_events: delta.active_events ?? snap.active_events,
          chart: [...snap.chart, delta.chart_point],
        },
        poRegular: delta.po_table ? regularOrders(delta.po_table, s.poRegular) : s.poRegular,
        logs: logs.length ? trim([...s.logs, ...logs]) : s.logs,
      }
    }),

  toggleAgent: (a) =>
    set((s) => {
      const next = new Set(s.logFilter)
      if (next.has(a)) next.delete(a)
      else next.add(a)
      return { logFilter: next }
    }),

  control: async (action, extra) => {
    try {
      const r = await api.control({ action, ...extra })
      set((s) => (s.snapshot ? { snapshot: { ...s.snapshot, status: r.status, speed: r.speed } } : {}))
    } catch (e) {
      set({ notice: failure(e) })
    }
  },

  triggerEvent: async (type, payload) => {
    try {
      await api.event({ type, payload })
    } catch (e) {
      set({ notice: failure(e) })
    }
  },

  openFormula: async (skuId) => {
    // same SKU = refresh in place (no flicker); a new SKU clears the old numbers
    set((s) => (s.selectedSku === skuId ? {} : { selectedSku: skuId, formula: null }))
    try {
      const formula = await api.formula(skuId)
      if (get().selectedSku === skuId) set({ formula })
    } catch (e) {
      set({ notice: failure(e) })
    }
  },

  closeFormula: () => set({ selectedSku: null, formula: null }),
  setTab: (activeTab) => set({ activeTab }),
  setEslStore: (eslStore) => set({ eslStore }),
  exportReport: async () => {
    try {
      await api.report()
    } catch (e) {
      set({ notice: failure(e) })
    }
  },
  dismissNotice: () => set({ notice: null }),

  selectFrame: (id) =>
    set((s) => {
      if (s.vision.upload) URL.revokeObjectURL(s.vision.imageUrl)
      const f = FRAMES.find((x) => x.id === id) ?? FRAMES[0]
      return { vision: { frameId: id, imageUrl: f.src, upload: null, result: null, scanning: false } }
    }),

  selectUpload: (file) =>
    set((s) => {
      const error = rejectReason(file)
      if (error) return { vision: { ...s.vision, error } }
      if (s.vision.upload) URL.revokeObjectURL(s.vision.imageUrl)
      const imageUrl = URL.createObjectURL(file)
      return { vision: { frameId: 'custom', imageUrl, upload: file, result: null, scanning: false } }
    }),

  scan: async () => {
    const v = get().vision
    set({ vision: { ...v, scanning: true, error: undefined, result: null } })
    try {
      // Presets send their image too, so live mode can analyse it; cached mode uses the fixture.
      let source: Blob
      if (v.upload) source = v.upload
      else source = await (await fetch(v.imageUrl)).blob()
      const form = new FormData()
      if (v.frameId !== 'custom') form.append('frame_id', v.frameId)
      form.append('file', await shrinkForVision(source), 'frame.jpg')
      const result = await api.scan(form)
      if (get().vision.imageUrl === v.imageUrl) set((s) => ({ vision: { ...s.vision, result, scanning: false } }))
    } catch (e) {
      set((s) => ({ vision: { ...s.vision, scanning: false, error: failure(e) } }))
    }
  },
}))
