"""Simulation state. Plain dataclasses; no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

OPEN_HOUR = 7  # store open 07:00–21:59
CLOSE_HOUR = 22
DELIVERY_HOUR = 6
PO_HOUR = 21
CYCLE_TICKS = 168

AGENTS = (
    "SYSTEM",
    "VISION_AGENT",
    "RAG_KNOWLEDGE_AGENT",
    "DEMAND_AGENT",
    "PRICING_AGENT",
    "PROCUREMENT_AGENT",
)


def sim_time(tick: int) -> str:
    return f"D{tick // 24 + 1} {tick % 24:02d}:00"


def is_open(tick: int) -> bool:
    return OPEN_HOUR <= tick % 24 < CLOSE_HOUR


@dataclass(frozen=True)
class SkuConfig:
    sku_id: str
    name: str
    category: str
    unit_weight_kg: float
    base_price_usd: float
    unit_cost_usd: float
    sl_nominal_hours: float
    elasticity: float
    price_floor_ratio: float
    base_daily_units: float
    weather_exposure: float
    bundle_group: str | None
    supplier: str
    off: dict = field(default_factory=dict, hash=False, compare=False)

    @classmethod
    def from_dict(cls, d: dict) -> SkuConfig:
        sku = cls(**{k: d.get(k) for k in cls.__dataclass_fields__ if k in d})
        if not sku.elasticity < 0:
            raise ValueError(f"{sku.sku_id}: elasticity must be < 0, got {sku.elasticity}")
        if not 0 < sku.price_floor_ratio <= 1:
            raise ValueError(f"{sku.sku_id}: price_floor_ratio must be in (0, 1]")
        return sku


@dataclass
class SimConfig:
    skus: list[SkuConfig]
    hour_share: dict[str, list[float]]  # category -> 24 floats, sums to 1 over open hours
    dow_weight: dict[str, list[float]]  # category -> 7 floats, mean 1.0
    co2e_factor: dict[str, float]  # category -> kg CO2e per kg food
    seed: int = 42
    start_dow: int = 0
    traffic_rain_mult: float = 0.78
    rain_duration_h: int = 12
    humidity_spike_mult: float = 1.78
    cold_chain_sl_mult: float = 0.70
    bundle_rsl_threshold_h: float = 8
    bundle_discount: float = 0.65
    bundle_base_rate_per_h: float = 1.5
    store_a_par_mult: float = 1.25
    store_a_markdown: float = 0.50
    safety_z: float = 1.0
    max_demand_mult: float = 3.0
    price_hysteresis: float = 0.02
    auto_scan_every_h: int = 6
    rh_base: float = 60.0  # from weather snapshot
    p_heavy_rain: list[float] = field(default_factory=lambda: [0.0] * 7)  # per sim day
    camera_skus: tuple[str, ...] = ("STRW-01", "BANA-01")
    emergency_delivery_days: float = 0.5  # immediate cold-chain delivery size, days of demand

    def __post_init__(self) -> None:
        self.sku_by_id = {s.sku_id: s for s in self.skus}
        self.sku_index = {s.sku_id: i for i, s in enumerate(self.skus)}
        for s in self.skus:
            for table in (self.hour_share, self.dow_weight, self.co2e_factor):
                if s.category not in table:
                    raise ValueError(f"{s.sku_id}: category {s.category!r} missing from a table")


@dataclass
class Batch:
    batch_id: str
    sku_id: str
    qty: int
    received_tick: int
    sl_true: float  # physical truth, identical in A and B for the same delivery
    sl_known: float  # Store B's belief (Store A never updates beliefs)
    alpha_true: float = 1.0
    age_true: float = 0.0
    alpha_known: float = 1.0
    age_known: float = 0.0
    inspected: bool = False

    def split(self, n: int, new_id: str) -> Batch:
        """Move n units into a new batch with the same physical/known attributes."""
        assert 0 < n <= self.qty
        self.qty -= n
        return replace(self, batch_id=new_id, qty=n)


@dataclass
class Box:
    box_id: str
    items: list[Batch]
    base_total: float
    price: float
    created_tick: int
    status: str = "listed"  # listed | sold | expired
    closed_tick: int | None = None


@dataclass
class StoreState:
    name: str  # "A" | "B"
    batches: dict[str, list[Batch]]  # sku -> batches, kept FEFO-sorted
    price: dict[str, float]
    boxes: list[Box] = field(default_factory=list)
    pending_order: dict[str, int] = field(default_factory=dict)
    received: dict[str, int] = field(default_factory=dict)
    sold: dict[str, int] = field(default_factory=dict)
    wasted: dict[str, int] = field(default_factory=dict)
    revenue_usd: float = 0.0
    cost_received_usd: float = 0.0
    waste_kg: float = 0.0
    written_off_usd: float = 0.0

    def on_hand(self, sku_id: str) -> int:
        return sum(b.qty for b in self.batches[sku_id])

    def in_boxes(self, sku_id: str) -> int:
        return sum(
            i.qty
            for bx in self.boxes
            if bx.status == "listed"
            for i in bx.items
            if i.sku_id == sku_id
        )


@dataclass
class LogDraft:
    tick: int
    agent: str
    level: str  # info | action | warn
    message: str
    data: dict | None = None


@dataclass
class SimState:
    config: SimConfig
    a: StoreState
    b: StoreState
    tick: int = 0
    rh: float = 60.0
    beta_env: float = 1.0
    traffic: float = 1.0
    storm_start: int | None = None
    cold_chain_pending: set[str] = field(default_factory=set)
    event_log: list[dict] = field(default_factory=list)
    po_rows: list[dict] = field(default_factory=list)
    po_reason: str | None = None  # e.g. "rainstorm" when a weather event forced the recompute
    pricing: dict[str, dict] = field(default_factory=dict)  # last Store B breakdown per SKU
    chart: list[dict] = field(default_factory=list)
    next_id: int = 0

    @property
    def finished(self) -> bool:
        return self.tick >= CYCLE_TICKS

    def new_id(self, prefix: str) -> str:
        self.next_id += 1
        return f"{prefix}{self.next_id}"
