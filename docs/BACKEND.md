# Backend Specification — ShelfSense

FastAPI + Pydantic v2 on Python 3.12. The backend owns the simulation; the frontend only renders snapshots and sends commands.

## 1. Modules

| Module | Responsibility | May import |
|---|---|---|
| `app/sim/*` | Pure engine (see SIMULATION_ENGINE.md) | stdlib, numpy |
| `app/agents/*` | Wrap sim functions, emit `LogEntry`, call services | sim, services, rag |
| `app/services/*` | External APIs with timeouts + fallbacks | httpx, config |
| `app/rag/*` | Build/load index, retrieve chunks | numpy, services.gemini |
| `app/controller.py` | Owns `SimState`, asyncio loop, event queue, WS broadcast | agents, sim |
| `app/api/*` | HTTP + WS routes; validation only | controller, models |
| `app/models/*` | Pydantic contracts for API/WS | pydantic |

`app/sim` must never import from `agents`, `services`, `api` or `controller`. Add a test that enforces this (scan imports).

## 2. Environment variables (`.env.example`)

```
APP_ENV=dev
CORS_ORIGINS=http://localhost:5173
SIM_SEED=42
VISION_MODE=cached            # cached | live
GEMINI_API_KEY=
GEMINI_VISION_MODEL=          # set to a current free-tier multimodal Gemini model
GEMINI_EMBED_MODEL=           # set to a current Gemini embedding model
RAG_MODE=auto                 # auto (vector if key+index, else bm25) | vector | bm25
NOAA_ENABLED=true
NOAA_LAT=40.7128              # store location (NOAA covers US only)
NOAA_LON=-74.0060
NOAA_USER_AGENT=ShelfSense (contact: your-email@example.com)
HTTP_TIMEOUT_S=8
```

## 3. REST API

All under `/api`. JSON in/out. Errors: `{"error": {"code": "...", "message": "..."}}` with proper status.

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| GET | `/health` | — | `{status, version, vision_mode, rag_mode, noaa: "live"\|"snapshot"}` | Used by the "waking server" screen. |
| GET | `/sim/state` | — | `SimSnapshot` | Full snapshot (on page load / reconnect). |
| POST | `/sim/control` | `{action: "play"\|"pause"\|"fast_forward"\|"step"\|"reset", seed?: int, replay?: bool}` | `{status, tick, speed}` | `step` advances exactly one tick (great for debugging). |
| POST | `/sim/events` | `{type: "rainstorm"\|"cold_chain_delay", payload?: {...}}` | `{queued: true, apply_at_tick}` | Applied at the start of the next tick. |
| GET | `/sim/skus/{sku_id}/formula` | — | `FormulaBreakdown` | Values behind the current price (Zone C drawer). |
| POST | `/vision/scan` | multipart: `frame_id` (`frame1..3`) **or** `file` (jpg/png ≤ 5 MB), optional `sku_hint` | `VisionScanResult` | See AI_PIPELINE.md. |
| GET | `/meta/architecture` | — | `{nodes, edges}` | Feeds the System Architecture modal (live status per node). |
| GET | `/meta/weather` | — | `WeatherNow` | Header widget. |

## 4. WebSocket `/ws/sim`

Server → client messages (`type` discriminator):

```jsonc
{ "type": "hello", "snapshot": SimSnapshot }                  // on connect
{ "type": "tick", "tick": 37, "delta": TickDelta, "logs": LogEntry[] }
{ "type": "status", "status": "playing"|"paused"|"finished", "speed": 1|24 }
{ "type": "event_applied", "event": AppliedEvent }
```

Client → server: none required (commands go via REST). Send a ping every 20 s; server replies `pong`.

Broadcast cadence: one `tick` message per tick. In fast-forward (24 ticks/s) that's fine for a single client; if the UI lags, batch logs and send at most 10 messages/s.

## 5. Contracts (Pydantic → mirror in `frontend/src/types/contracts.ts`)

```python
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
    rsl_hours: float              # Store B's known RSL for the oldest batch
    printed_remaining_hours: float
    base_price: float
    current_price: float
    markdown_pct: float
    risk_state: Literal["ok", "surplus_risk", "floor_bound", "bundled", "sold_out"]
    store_a_price: float          # for comparison tooltip

class FormulaBreakdown(BaseModel):
    sku_id: str
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
    sources: list[str]            # e.g. ["USDA FoodKeeper: Strawberries (refrigerator)", "Favorita profile: berries"]

class PoRow(BaseModel):
    sku_id: str; supplier: str
    baseline_order: int; projected_carryover: int
    weather_modifier: float; ai_order: int
    waste_prevention_units: int; waste_prevention_kg: float

class Bundle(BaseModel):
    bundle_id: str
    items: list[dict]             # [{sku_id, name, qty}]
    base_total: float
    price: float
    created_tick: int
    expires_in_hours: float
    status: Literal["listed", "sold", "expired"]

class LogEntry(BaseModel):
    tick: int
    sim_time: str                 # "D2 14:00"
    agent: Literal["SYSTEM","VISION_AGENT","RAG_KNOWLEDGE_AGENT","DEMAND_AGENT","PRICING_AGENT","PROCUREMENT_AGENT"]
    level: Literal["info","action","warn"]
    message: str
    data: dict | None = None      # structured details (numbers, citations)

class ChartPoint(BaseModel):
    tick: int
    waste_kg_a: float; waste_kg_b: float
    revenue_a: float; revenue_b: float

class SimSnapshot(BaseModel):
    tick: int; status: str; speed: int; seed: int
    weather: WeatherNow
    kpis: Kpis
    esl: list[EslView]
    po_table: list[PoRow]
    bundles: list[Bundle]
    chart: list[ChartPoint]
    active_events: list[AppliedEvent]

class TickDelta(BaseModel):          # what changed this tick
    kpis: Kpis
    esl: list[EslView]               # send all 8; small
    po_table: list[PoRow] | None     # only when changed
    bundles: list[Bundle] | None
    chart_point: ChartPoint
    weather: WeatherNow | None
```

### 5.1 Contract additions (2026-11-16, `app/models/contracts.py` is the source of truth)
- `SimSnapshot.logs` — last 200 log entries, so a reconnecting client can refill Zone E.
- `PoRow.delivery_tick`, `PoRow.reason` (e.g. `"rainstorm"` → Zone D highlight).
- `FormulaBreakdown.tick`, `p_current`, `risk`, `floor_bound`.
- `WeatherNow` = `{source, location, temperature_f, precip_probability_pct, short_forecast, relative_humidity_pct (sim, incl. storm), traffic_mult, storm_active}`.
- `AppliedEvent` = `{tick, type, payload, active_until_tick}`; `TickDelta.active_events` (only when changed).
- `ControlRequest.scenario: "none" | "demo"` (used by reset).

## 6. Agents

All agents share an interface:

```python
class Agent(Protocol):
    name: AgentName
    def run(self, state: SimState, ctx: TickContext) -> list[LogEntry]: ...
```

`Orchestrator.step()` calls the sim engine's tick phases in the order of SIMULATION_ENGINE §10 and lets each agent add log entries at its phase. **Logging rules** (keep Zone E readable):
- Log a `PRICING_AGENT` line only when an ESL price is actually republished (after hysteresis).
- Log `DEMAND_AGENT` once per hour summarising traffic and notable SKUs, not 8 lines per tick.
- `PROCUREMENT_AGENT` logs at 21:00 and whenever a weather event forces a PO recompute.
- `RAG_KNOWLEDGE_AGENT` logs the retrieved source title + chunk id + similarity score.
- Messages are short, numeric and specific, e.g. `STRW-01 RSL 19.0h (was 72h printed). V_target 2.6/h > V_forecast 1.7/h → ΔQ +53% → ΔP −26% → $3.69`.

Optional: if `GEMINI_API_KEY` is set and `EXPLAIN_MODE=llm`, the Pricing agent can ask Gemini to rephrase the numeric message into one plain-English sentence — numbers are passed in, never generated. Default is the template string.

## 7. Services (all: `httpx.AsyncClient`, timeout, 1 retry, fallback, cache)

- `noaa.py` — `GET https://api.weather.gov/points/{lat},{lon}` → forecast + hourly forecast URLs. Requires a `User-Agent` header. Cache 30 min. Fallback: `data/seed/weather_snapshot.json`.
- `openfoodfacts.py` — `GET https://world.openfoodfacts.org/api/v2/product/{barcode}.json`. Only used by the seed script (and optionally for custom-image SKU lookup). Fallback: values already in `skus.json`.
- `gemini.py` — vision call and embed call. See AI_PIPELINE.md. Never raise into the sim loop; return `None` and let the caller fall back.

## 8. Testing
- `tests/test_sim_*.py` — every row of SIMULATION_ENGINE §12, plus property tests (no negative stock, waste + sold + on_hand + in_bundles == received for every SKU — **conservation of units**).
- `tests/test_api.py` — FastAPI `TestClient`: control flow, events queue, scan with cached fixture, WS hello + 3 ticks via `step`.
- `tests/test_imports.py` — `app.sim` imports nothing from the app outside `app.sim`.
- No test hits the network; services are faked.
