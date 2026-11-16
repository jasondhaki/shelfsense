// Mirrors backend/app/models/contracts.py — change both together (CLAUDE.md rule 5).

export type AgentName =
  | 'SYSTEM'
  | 'VISION_AGENT'
  | 'RAG_KNOWLEDGE_AGENT'
  | 'DEMAND_AGENT'
  | 'PRICING_AGENT'
  | 'PROCUREMENT_AGENT'
export type SimStatus = 'paused' | 'playing' | 'finished'
export type ControlAction = 'play' | 'pause' | 'fast_forward' | 'step' | 'reset'
export type EventType = 'rainstorm' | 'cold_chain_delay'
export type RiskState = 'ok' | 'surplus_risk' | 'floor_bound' | 'bundled' | 'sold_out'
export type Ethylene = 'producer' | 'sensitive' | 'neutral'

export interface Kpis {
  waste_reduction_pct: number | null
  food_diverted_kg: number
  co2e_avoided_kg: number
  net_margin_recovered_usd: number
  waste_kg_a: number
  waste_kg_b: number
}

export interface EslView {
  sku_id: string
  name: string
  category: string
  nutri_score: string | null
  packaging: string | null
  ethylene: Ethylene | null
  on_hand: number
  forecast_24h: number
  surplus_risk_units: number
  rsl_hours: number
  printed_remaining_hours: number
  base_price: number
  current_price: number
  markdown_pct: number
  risk_state: RiskState
  store_a_price: number
  shelf_life_hours: number // nominal (FoodKeeper) life; freshness % = rsl_hours / this
}

export interface FormulaBreakdown {
  sku_id: string
  tick: number
  rsl_known: number
  alpha_known: number
  beta_sku: number
  inventory: number
  v_target: number
  v_forecast: number
  delta_q_pct: number
  elasticity: number
  elasticity_is_assumed: boolean
  delta_p_pct: number
  p_raw: number
  p_floor: number
  p_new: number
  p_current: number
  risk: boolean
  floor_bound: boolean
  sources: string[]
}

export interface PoRow {
  sku_id: string
  supplier: string
  baseline_order: number
  projected_carryover: number
  weather_modifier: number
  ai_order: number
  waste_prevention_units: number
  waste_prevention_kg: number
  delivery_tick: number
  reason: string | null
}

export interface BundleItem {
  sku_id: string
  name: string
  qty: number
}

export interface Bundle {
  bundle_id: string
  items: BundleItem[]
  base_total: number
  price: number
  created_tick: number
  expires_in_hours: number
  status: 'listed' | 'sold' | 'expired'
}

export interface LogEntry {
  tick: number
  sim_time: string
  agent: AgentName
  level: 'info' | 'action' | 'warn'
  message: string
  data: Record<string, unknown> | null
}

export interface ChartPoint {
  tick: number
  waste_kg_a: number
  waste_kg_b: number
  revenue_a: number
  revenue_b: number
  co2e_avoided_kg: number
  net_margin_recovered_usd: number
}

export interface WeatherNow {
  source: 'live' | 'snapshot'
  location: string
  temperature_f: number | null
  precip_probability_pct: number | null
  short_forecast: string | null
  relative_humidity_pct: number
  traffic_mult: number
  storm_active: boolean
}

export interface AppliedEvent {
  tick: number
  type: string
  payload: Record<string, unknown>
  active_until_tick: number | null
}

export interface SimSnapshot {
  tick: number
  status: SimStatus
  speed: number
  seed: number
  weather: WeatherNow
  kpis: Kpis
  esl: EslView[]
  esl_a: EslView[] // baseline store's labels (printed-date view)
  po_table: PoRow[]
  bundles: Bundle[]
  chart: ChartPoint[]
  active_events: AppliedEvent[]
  logs: LogEntry[]
}

export interface TickDelta {
  kpis: Kpis
  esl: EslView[]
  esl_a: EslView[]
  po_table: PoRow[] | null
  bundles: Bundle[] | null
  chart_point: ChartPoint
  weather: WeatherNow | null
  active_events: AppliedEvent[] | null
}

export interface ControlRequest {
  action: ControlAction
  seed?: number
  replay?: boolean
  scenario?: 'none' | 'demo'
}

export interface ControlResponse {
  status: SimStatus
  tick: number
  speed: number
}

export interface EventRequest {
  type: EventType
  payload?: Record<string, unknown>
}

export interface EventResponse {
  queued: boolean
  apply_at_tick: number
}

export interface ApiError {
  error: { code: string; message: string }
}

// WebSocket server -> client
export type TickMessage = { type: 'tick'; tick: number; delta: TickDelta; logs: LogEntry[] }
export type ServerMessage =
  | { type: 'hello'; snapshot: SimSnapshot }
  | TickMessage
  | { type: 'status'; status: SimStatus; speed: number }
  | { type: 'event_applied'; event: AppliedEvent }
  | { type: 'pong' }

// --- vision (AI_PIPELINE §1) ---
export type FrameId = 'frame1' | 'frame2' | 'frame3'
export type Severity = 'optimal' | 'accelerated_ripening' | 'clearance_required'

export interface Detection {
  label: string
  box_2d: [number, number, number, number] // [ymin, xmin, ymax, xmax], 0..1000
  severity: Severity
  defects: string[]
  confidence: number
}

export interface VisionExtraction {
  detections: Detection[]
  visual_quality_score: number | null
  defects_detected: string[]
  estimated_unit_count: number
  primary_sku_label: string
  rationale: string
}

export interface Citation {
  source: string
  title: string
  chunk_id: string
  text: string
  url: string
  score: number | null
  mode: 'bm25' | 'vector' | null
}

export interface VisionScanResult {
  frame_id: FrameId | 'custom'
  mode: 'cached' | 'live'
  extraction: VisionExtraction
  target_sku: string | null
  alpha_vision: number
  rsl_before_hours: number | null
  printed_remaining_hours: number | null
  rsl_after_hours: number | null
  foodkeeper_citation: Citation | null
  applied_at_tick: number | null
  note: string | null
}

// --- accounts (backend/app/api/auth.py) ---
export interface UserOut {
  id: string
  email: string
  name: string
  store: string
}

export interface AuthResponse {
  token: string
  user: UserOut
}

export interface SignupRequest {
  email: string
  password: string
  name: string
  store: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface ProfileUpdate {
  name: string
  store: string
}

// --- meta (Phase 8) ---
export interface ArchNode {
  id: string
  label: string
  layer: 'source' | 'knowledge' | 'agent' | 'core' | 'output'
  status: 'live' | 'fallback' | 'static'
  detail: string
  agent: AgentName | null
}

export interface ArchEdge {
  source: string
  target: string
}

export interface Architecture {
  nodes: ArchNode[]
  edges: ArchEdge[]
}
