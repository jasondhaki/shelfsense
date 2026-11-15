"""API / WebSocket contracts (BACKEND §5). Mirror every change in
frontend/src/types/contracts.ts (CLAUDE.md rule 5)."""

from typing import Literal

from pydantic import BaseModel

AgentName = Literal[
    "SYSTEM",
    "VISION_AGENT",
    "RAG_KNOWLEDGE_AGENT",
    "DEMAND_AGENT",
    "PRICING_AGENT",
    "PROCUREMENT_AGENT",
]
SimStatus = Literal["paused", "playing", "finished"]
ControlAction = Literal["play", "pause", "fast_forward", "step", "reset"]
EventType = Literal["rainstorm", "cold_chain_delay"]


class Kpis(BaseModel):
    waste_reduction_pct: float | None
    food_diverted_kg: float
    co2e_avoided_kg: float
    net_margin_recovered_usd: float
    waste_kg_a: float
    waste_kg_b: float


class EslView(BaseModel):
    sku_id: str
    name: str
    category: str
    nutri_score: str | None
    packaging: str | None
    ethylene: Literal["producer", "sensitive", "neutral"] | None
    on_hand: int
    forecast_24h: float
    surplus_risk_units: int
    rsl_hours: float  # Store B's known RSL for the oldest batch
    printed_remaining_hours: float
    base_price: float
    current_price: float
    markdown_pct: float
    risk_state: Literal["ok", "surplus_risk", "floor_bound", "bundled", "sold_out"]
    store_a_price: float


class FormulaBreakdown(BaseModel):
    sku_id: str
    tick: int
    rsl_known: float
    alpha_known: float
    beta_sku: float
    inventory: int
    v_target: float
    v_forecast: float
    delta_q_pct: float
    elasticity: float
    elasticity_is_assumed: bool = True
    delta_p_pct: float
    p_raw: float
    p_floor: float
    p_new: float
    p_current: float
    risk: bool
    floor_bound: bool
    sources: list[str]


class PoRow(BaseModel):
    sku_id: str
    supplier: str
    baseline_order: int
    projected_carryover: int
    weather_modifier: float
    ai_order: int
    waste_prevention_units: int
    waste_prevention_kg: float
    delivery_tick: int
    reason: str | None = None  # e.g. "rainstorm" when a weather event forced the recompute


class BundleItem(BaseModel):
    sku_id: str
    name: str
    qty: int


class Bundle(BaseModel):
    bundle_id: str
    items: list[BundleItem]
    base_total: float
    price: float
    created_tick: int
    expires_in_hours: float
    status: Literal["listed", "sold", "expired"]


class LogEntry(BaseModel):
    tick: int
    sim_time: str  # "D2 14:00"
    agent: AgentName
    level: Literal["info", "action", "warn"]
    message: str
    data: dict | None = None


class ChartPoint(BaseModel):
    tick: int
    waste_kg_a: float
    waste_kg_b: float
    revenue_a: float
    revenue_b: float


class WeatherNow(BaseModel):
    source: Literal["live", "snapshot"]
    location: str
    temperature_f: float | None
    precip_probability_pct: float | None
    short_forecast: str | None
    relative_humidity_pct: float  # inside the sim, incl. storm spike
    traffic_mult: float
    storm_active: bool


class AppliedEvent(BaseModel):
    tick: int
    type: str
    payload: dict
    active_until_tick: int | None = None  # rainstorm window; None = pending/instant


class SimSnapshot(BaseModel):
    tick: int
    status: SimStatus
    speed: int
    seed: int
    weather: WeatherNow
    kpis: Kpis
    esl: list[EslView]
    po_table: list[PoRow]
    bundles: list[Bundle]
    chart: list[ChartPoint]
    active_events: list[AppliedEvent]
    logs: list[LogEntry]  # recent log tail, so a reconnecting client can refill Zone E


class TickDelta(BaseModel):
    kpis: Kpis
    esl: list[EslView]
    po_table: list[PoRow] | None  # only when changed
    bundles: list[Bundle] | None  # only when changed
    chart_point: ChartPoint
    weather: WeatherNow | None  # only when changed
    active_events: list[AppliedEvent] | None  # only when changed


# --- requests / responses ----------------------------------------------------------


class ControlRequest(BaseModel):
    action: ControlAction
    seed: int | None = None
    replay: bool = False
    scenario: Literal["none", "demo"] | None = None


class ControlResponse(BaseModel):
    status: SimStatus
    tick: int
    speed: int


class EventRequest(BaseModel):
    type: EventType
    payload: dict = {}


class EventResponse(BaseModel):
    queued: bool
    apply_at_tick: int
