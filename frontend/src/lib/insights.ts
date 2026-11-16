import type { AgentName, ChartPoint, EslView, LogEntry, SimSnapshot } from '../types/contracts'

export const NUTRI: Record<string, string> = {
  a: 'bg-[#038141] text-white',
  b: 'bg-[#85BB2F] text-black',
  c: 'bg-[#FECB02] text-black',
  d: 'bg-[#EE8100] text-black',
  e: 'bg-[#E63E11] text-white',
}

export const productImg = (skuId: string) => `/products/${skuId}.jpg`

/** Share of the item's nominal (FoodKeeper) shelf life still left on the oldest batch, 0–1. */
export const freshness = (e: EslView) =>
  e.on_hand && e.shelf_life_hours > 0 ? Math.min(Math.max(e.rsl_hours / e.shelf_life_hours, 0), 1) : 0

export const atRisk = (e: EslView) =>
  e.on_hand > 0 && (e.rsl_hours < 24 || (e.risk_state !== 'ok' && e.risk_state !== 'sold_out'))

/** Short names for cards ("Organic Strawberries 1 lb" → "Organic Strawberries"). */
export const shortName = (name: string) => name.replace(/\s+(\(.*\)|\d.*)$/, '')

// --- KPI series from the hourly chart history (exact, not client-side guesses) ---

export type KpiKey = 'reduction' | 'diverted' | 'co2e' | 'margin'

export function kpiAt(p: ChartPoint, k: KpiKey): number | null {
  switch (k) {
    case 'reduction':
      return p.waste_kg_a > 0 ? ((p.waste_kg_a - p.waste_kg_b) / p.waste_kg_a) * 100 : null
    case 'diverted':
      return p.waste_kg_a - p.waste_kg_b
    case 'co2e':
      return p.co2e_avoided_kg
    case 'margin':
      return p.net_margin_recovered_usd
  }
}

export function series(chart: ChartPoint[], k: KpiKey): number[] {
  return chart.map((p) => kpiAt(p, k)).filter((v): v is number => v !== null)
}

/** Change over the last 24 simulated hours, or null before a day has passed. */
export function dayChange(chart: ChartPoint[], k: KpiKey): number | null {
  if (chart.length < 25) return null
  const now = kpiAt(chart[chart.length - 1], k)
  const before = kpiAt(chart[chart.length - 25], k)
  return now === null || before === null ? null : now - before
}

// --- agents ---

export const AGENT_CHIPS: { agent: AgentName; label: string; tone: string }[] = [
  { agent: 'DEMAND_AGENT', label: 'Forecast', tone: 'text-agent-demand' },
  { agent: 'PRICING_AGENT', label: 'Pricing', tone: 'text-agent-pricing' },
  { agent: 'VISION_AGENT', label: 'Vision', tone: 'text-agent-vision' },
  { agent: 'PROCUREMENT_AGENT', label: 'Rebalancer', tone: 'text-agent-procurement' },
  { agent: 'RAG_KNOWLEDGE_AGENT', label: 'Knowledge', tone: 'text-agent-rag' },
]

/** An agent counts as active if it logged something in the last 6 simulated hours. */
export const activeAgents = (logs: LogEntry[], tick: number) =>
  new Set(logs.filter((l) => l.tick >= tick - 6).map((l) => l.agent))

// --- alerts (derived from the live snapshot; nothing invented) ---

export interface Alert {
  id: string
  tone: 'crit' | 'warn' | 'info'
  title: string
  detail: string
  skuId?: string
  goTo?: 'orders' | 'pricing' | 'forecast'
}

export function deriveAlerts(s: SimSnapshot): Alert[] {
  const out: Alert[] = []
  for (const e of s.esl) {
    if (e.on_hand === 0 || e.rsl_hours >= 24) continue
    const marked = e.markdown_pct > 0.005
    out.push({
      id: `rsl-${e.sku_id}`,
      tone: e.rsl_hours < 8 ? 'crit' : 'warn',
      title: shortName(e.name),
      detail: `${e.on_hand} left, expires in ${e.rsl_hours.toFixed(1)} h${
        marked ? ` · auto-marked down ${Math.round(e.markdown_pct * 100)}%` : ''
      }`,
      skuId: e.sku_id,
    })
  }
  const storm = s.active_events.find((e) => e.type === 'rainstorm')
  if (storm) {
    out.push({
      id: 'storm',
      tone: 'info',
      title: 'Rainstorm in progress',
      detail: `Foot traffic ×${s.weather.traffic_mult.toFixed(2)} — orders and prices adjusted`,
      goTo: 'forecast',
    })
  }
  const po = [...s.po_table].sort(
    (a, b) => Math.abs(b.ai_order - b.baseline_order) - Math.abs(a.ai_order - a.baseline_order),
  )[0]
  if (po && po.ai_order !== po.baseline_order) {
    const name = shortName(s.esl.find((e) => e.sku_id === po.sku_id)?.name ?? po.sku_id)
    out.push({
      id: `po-${po.sku_id}`,
      tone: 'info',
      title: po.ai_order < po.baseline_order ? 'Order throttled' : 'Restock suggestion',
      detail: `${name}: order ${po.ai_order} (baseline ${po.baseline_order})${po.reason ? ` — ${po.reason}` : ''}`,
      goTo: 'orders',
    })
  }
  const boxes = s.bundles.filter((b) => b.status === 'listed').length
  if (boxes) {
    out.push({
      id: 'boxes',
      tone: 'info',
      title: `${boxes} surplus box${boxes > 1 ? 'es' : ''} listed`,
      detail: 'Short-dated items bundled at a discount',
      goTo: 'pricing',
    })
  }
  const rank = { crit: 0, warn: 1, info: 2 }
  return out.sort((a, b) => rank[a.tone] - rank[b.tone])
}

export function greeting(d = new Date()): string {
  const h = d.getHours()
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
}
