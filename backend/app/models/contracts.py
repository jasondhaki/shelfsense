"""API / WebSocket contracts (BACKEND §5). Mirror every change in
frontend/src/types/contracts.ts (CLAUDE.md rule 5)."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

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
    shelf_life_hours: float  # nominal (FoodKeeper) life; freshness % = rsl_hours / this


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
    co2e_avoided_kg: float
    net_margin_recovered_usd: float


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
    esl_a: list[EslView]  # baseline store's labels (printed-date view)
    po_table: list[PoRow]
    bundles: list[Bundle]
    chart: list[ChartPoint]
    active_events: list[AppliedEvent]
    logs: list[LogEntry]  # recent log tail, so a reconnecting client can refill Zone E


class TickDelta(BaseModel):
    kpis: Kpis
    esl: list[EslView]
    esl_a: list[EslView]
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


class EventPayload(BaseModel):
    """Typed so junk can't reach the engine, the event log or every WebSocket client."""

    model_config = {"extra": "forbid"}
    skus: list[str] | None = Field(None, max_length=8)  # cold_chain_delay; None = default SKUs
    immediate: bool = False  # cold_chain_delay: emergency delivery now


class EventRequest(BaseModel):
    type: EventType
    payload: EventPayload = EventPayload()


class EventResponse(BaseModel):
    queued: bool
    apply_at_tick: int


# --- vision (AI_PIPELINE §1) --------------------------------------------------------

SkuLabel = Literal[
    "strawberries",
    "bananas",
    "avocados",
    "spinach",
    "cherry_tomatoes",
    "sourdough",
    "salmon",
    "milk",
    "other",
]
Severity = Literal["optimal", "accelerated_ripening", "clearance_required"]
Defect = Literal[
    "stem_browning",
    "surface_moisture",
    "ethylene_bruising",
    "sugar_spotting",
    "mold",
    "wilting",
    "soft_spots",
    "discoloration",
    "leakage",
]
FrameId = Literal["frame1", "frame2", "frame3"]


class Detection(BaseModel):
    label: SkuLabel
    box_2d: list[int] = Field(min_length=4, max_length=4)  # [ymin, xmin, ymax, xmax], 0..1000
    severity: Severity
    defects: list[Defect]
    confidence: float = Field(ge=0, le=1)

    @field_validator("box_2d")
    @classmethod
    def _box(cls, v: list[int]) -> list[int]:
        ymin, xmin, ymax, xmax = v
        if not (0 <= ymin < ymax <= 1000 and 0 <= xmin < xmax <= 1000):
            raise ValueError("box_2d must be [ymin, xmin, ymax, xmax] within 0..1000")
        return v


class VisionExtraction(BaseModel):
    detections: list[Detection]
    visual_quality_score: float | None = Field(default=None, ge=1, le=10)
    defects_detected: list[Defect]
    estimated_unit_count: int = Field(ge=0)
    primary_sku_label: SkuLabel
    rationale: str


class Citation(BaseModel):
    source: str
    title: str
    chunk_id: str
    text: str
    url: str = ""
    score: float | None = None
    mode: Literal["bm25", "vector"] | None = None


class VisionScanResult(BaseModel):
    frame_id: FrameId | Literal["custom"]
    mode: Literal["cached", "live"]
    extraction: VisionExtraction
    target_sku: str | None  # None when the image isn't one of our SKUs ("other")
    alpha_vision: float
    rsl_before_hours: float | None  # Store B belief, oldest batch, before the scan
    printed_remaining_hours: float | None
    rsl_after_hours: float | None
    foodkeeper_citation: Citation | None
    applied_at_tick: int | None  # tick the shelf-life override is applied (next tick)
    note: str | None = None  # e.g. why live mode fell back to the cached result


# --- meta (Phase 8) ------------------------------------------------------------------


class ArchNode(BaseModel):
    id: str
    label: str
    layer: Literal["source", "knowledge", "agent", "core", "output"]
    status: Literal[
        "live", "fallback", "static"
    ]  # live = running/connected; fallback = offline path
    detail: str
    agent: AgentName | None = None  # ties the node to log lines for the activity pulse


class ArchEdge(BaseModel):
    source: str
    target: str


class Architecture(BaseModel):
    nodes: list[ArchNode]
    edges: list[ArchEdge]


class ExplainRequest(BaseModel):
    agent: AgentName
    message: str = Field(max_length=2000)
    data: dict | None = None


class Explanation(BaseModel):
    text: str
    mode: Literal["llm", "template"]
    provider: Literal["gemini", "ollama"] | None = None
    model: str | None = None
    guardrail: str | None = None  # why an LLM answer was replaced by the template
    facts: list[str]  # knowledge-graph facts given to the model
    citations: list[Citation]
