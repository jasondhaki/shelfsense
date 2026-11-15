# Architecture — ShelfSense (FoodSphere AI domain)

## 1. System at a glance

```
┌──────────────────────────── Browser (React + Vite) ────────────────────────────┐
│ Zone A Telemetry/Controls │ Zone B Smart-Cam │ Zone C ESL Matrix │ Zone E Log   │
│                           │                  │ Zone D PO / Bundles              │
│                 Zustand store  ◄── WebSocket /ws/sim (tick snapshots + logs)    │
│                                ──► REST /api/* (controls, events, vision scan)  │
└────────────────────────────────────────┬───────────────────────────────────────┘
                                         │
┌──────────────────────────── FastAPI backend ────────────────────────────────────┐
│ api/ (REST + WS)                                                                 │
│   └── SimController (asyncio loop: play / pause / fast-forward / reset)          │
│          └── Orchestrator ── runs agents in a fixed order each tick              │
│                 ├── DemandAgent        ─┐                                         │
│                 ├── PricingAgent        │  pure functions from app/sim/           │
│                 ├── ProcurementAgent    │  (deterministic math)                   │
│                 ├── BundlingAgent      ─┘                                         │
│                 ├── VisionAgent  ──► services/gemini.py  (or cached fixture)      │
│                 └── RagKnowledgeAgent ──► rag/retriever.py (vector or BM25)       │
│          └── AgentBus (collects LogEntry objects → streamed to Zone E)           │
│ services/: noaa.py, openfoodfacts.py, gemini.py (all with offline fallback)      │
│ data/seed/*.json  data/rag/  data/fixtures/vision/                               │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Key idea:** "agents" are thin wrappers. The real decisions come from pure, unit-tested functions in `app/sim/`. An agent = (call the pure function) + (emit a log entry explaining it) + (optionally ask the RAG agent for a citation). This keeps the demo deterministic while still looking and reading like a multi-agent system.

## 2. Repository layout

```
shelfsense/
├── CLAUDE.md
├── .env.example
├── docs/
│   ├── PRODUCT_PLAN.md          # original blueprint (copy of the master plan)
│   ├── ARCHITECTURE.md
│   ├── SIMULATION_ENGINE.md
│   ├── BACKEND.md
│   ├── FRONTEND.md
│   ├── DATA_SOURCES.md
│   ├── AI_PIPELINE.md
│   └── IMPLEMENTATION_PLAN.md
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py              # FastAPI app factory, CORS, router mount
│   │   ├── config.py            # pydantic-settings, reads .env
│   │   ├── models/              # Pydantic API/WS contracts
│   │   ├── api/                 # routes_sim.py, routes_vision.py, routes_meta.py, ws.py
│   │   ├── sim/                 # PURE engine — no I/O
│   │   │   ├── state.py         # dataclasses: SimState, StoreState, Batch, SkuConfig…
│   │   │   ├── rng.py           # seeded RNG, common random numbers
│   │   │   ├── shelf_life.py    # RSL / effective-age model
│   │   │   ├── demand.py        # hourly forecast + realised demand
│   │   │   ├── pricing.py       # velocity gap + elasticity discount
│   │   │   ├── procurement.py   # order throttling + Store A static reorder
│   │   │   ├── bundling.py      # flash surplus bundles
│   │   │   ├── events.py        # rainstorm, cold-chain delay, vision override
│   │   │   ├── kpi.py           # waste %, kg diverted, margin recovered
│   │   │   ├── engine.py        # step(state, events) -> (state, logs)
│   │   │   └── cli.py           # headless runner
│   │   ├── agents/              # bus.py, orchestrator.py, *_agent.py
│   │   ├── services/            # gemini.py, noaa.py, openfoodfacts.py
│   │   ├── rag/                 # build_index.py, retriever.py
│   │   └── controller.py        # SimController (asyncio loop, owns SimState)
│   ├── data/
│   │   ├── seed/                # skus.json, foodkeeper.json, sales_profile.json, faostat.json, weather_snapshot.json
│   │   ├── rag/                 # corpus/*.md, index.npz, bm25.json
│   │   └── fixtures/vision/     # frame1.json … frame3.json (cached Gemini outputs)
│   ├── scripts/                 # build_seed_*.py — offline data prep, run manually
│   └── tests/
└── frontend/
    ├── index.html
    ├── vite.config.ts
    ├── tailwind.config.ts
    └── src/
        ├── main.tsx, App.tsx
        ├── zones/               # TelemetryBar, SmartCamInspector, EslMatrix, ExecutionModules, AgentLog
        ├── components/          # KpiCard, EslCard, FormulaDrawer, BoundingBoxCanvas, ArchitectureModal…
        ├── store/simStore.ts    # Zustand
        ├── lib/                 # ws.ts, api.ts, format.ts
        ├── types/contracts.ts   # mirrors backend/app/models
        └── assets/frames/       # preset CCTV images
```

## 3. Runtime flow

### 3.1 Tick loop
`SimController` owns one `SimState`. On `play`, an asyncio task calls `orchestrator.step()` every `1 / speed` seconds:
- `1x` → 1 tick per second (1 sim hour / s).
- `fast_forward` → ~24 ticks/s until tick 168 or pause.
- Each step returns `(new_state, log_entries)`. The controller broadcasts a `tick` WS message containing a **compact snapshot** (KPIs, per-SKU ESL view, PO table, bundles, chart point) plus new log entries.

User actions (events, vision results) are **queued** and applied at the start of the next tick, so they are recorded in the event timeline and replayable.

### 3.2 Event timeline & replay
Every applied event is stored as `{tick, type, payload}` in `state.event_log`. `POST /api/sim/reset` with `replay=true` re-runs the same seed + timeline — useful for testing and for "show me that again" in a demo.

### 3.3 Vision scan
`POST /api/vision/scan` → VisionAgent:
1. Preset frame + `VISION_MODE=cached` (default) → load fixture JSON.
2. Preset or custom image + `VISION_MODE=live` and key present → call Gemini; on error/timeout fall back to fixture (preset) or return a clear error (custom).
3. Map `visual_quality_score` + defects → `alpha_vision` (AI_PIPELINE §3).
4. RAG agent fetches FoodKeeper rules for the SKU → citation in log.
5. Queue a `vision_override` event for the target SKU's newest batch. The response returns the detections + RSL before/after so Zone B can render immediately.

## 4. Data flow per source
| Source | Fetched when | Stored as | Used by |
|---|---|---|---|
| USDA FoodKeeper | offline script | `data/seed/foodkeeper.json` + RAG corpus | `shelf_life.py`, RAG |
| Open Food Facts | offline script (live optional) | merged into `skus.json` | ESL badges, RAG |
| Kaggle (Favorita) | offline script | `data/seed/sales_profile.json` (aggregates only) | `demand.py` |
| NOAA api.weather.gov | on startup + every N min (optional) | in memory; fallback `weather_snapshot.json` | `events.py`, header widget |
| FAOSTAT / FAO FLW DB | offline script | `data/seed/faostat.json` | Store A calibration, kg/CO₂e KPI |

Details in `DATA_SOURCES.md`.

## 5. Deployment (free tier)
- **Frontend:** Vercel, `VITE_API_URL` and `VITE_WS_URL` env vars.
- **Backend:** Render free web service (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`). Free instances sleep when idle → the frontend shows a "waking server…" state and retries the WS connection.
- **Single-user assumption:** one shared SimState per process is fine for a demo. If two people open it they share the simulation. (Optional later: per-session state keyed by a client id.)

## 6. Decisions log
Add one line per decision: date — decision — reason.

- 2026-11-15 — Python backend owns the simulation; frontend is a view. — Keeps agents, RAG and vision in one language; engine testable with pytest.
- 2026-11-15 — Agents are deterministic wrappers over pure functions; LLM only for vision extraction and explanation text. — Reproducible demo, no hallucinated prices.
- 2026-11-15 — RSL uses an effective-age model instead of the blueprint's single formula. — Blueprint formula makes spoilage time independent of α (see SIMULATION_ENGINE §0).
- 2026-11-15 — Common random numbers for Store A/B demand. — Fair comparison; differences come from policy, not luck.
- 2026-11-15 — Local `.npz` vector index + BM25 fallback instead of a hosted vector DB. — Corpus is small (<500 chunks); free; fits Render's 512 MB RAM.
- 2026-11-15 — Kaggle raw data is not committed; only derived aggregates. — Competition-data licence terms.
- 2026-11-15 — Frontend pinned to React 18 + Tailwind v3 (Vite template now defaults to React 19 / Tailwind v4). — Matches the stack in CLAUDE.md; v3 keeps tokens in `tailwind.config.ts` as FRONTEND §2 describes.
- 2026-11-15 — Lint with `oxlint` (ships with the current Vite template) instead of ESLint. — Zero-config, fast; `npm run lint` contract unchanged.
- 2026-11-15 — Vite proxy targets `127.0.0.1:8000`, not `localhost`. — On Windows `localhost` resolves to `::1`, which other local services (e.g. Docker) may hold.
- 2026-11-16 — With several batches, V_forecast uses the horizon `ceil(RSL_known)` of the batch that sets V_target. — §5.1 gives one horizon but a FEFO max over batches; the binding batch is the one whose risk we're pricing.
- 2026-11-16 — Seed-file loading lives in `app/sim/cli.py`; the engine modules stay I/O-free. — Keeps rule 3 while giving the CLI and the controller one loader.
- 2026-11-16 — `step()` mutates and returns the state it is given. — Copying the full state each tick buys nothing; determinism comes from the keyed RNG + fixed order, and replay rebuilds from seed.
- 2026-11-16 — Bundling logs use the `PRICING_AGENT` tag. — No bundling tag exists in the fixed tag list; last-mile clearance is a pricing action.
- 2026-11-16 — Store B PO "carryover" is clamped at ≥ 0; a mid-day recompute (rainstorm) uses expected sales for the rest of today, from the current hour. — §7.2 formula can go negative; the current hour hasn't sold yet when an event is applied.
- 2026-11-16 — Immediate cold-chain delivery = ceil(0.5 × base_daily_units) to both stores (`emergency_delivery_days`). — §8 doesn't size it; half a day is visible in the demo without swamping the shelf.
- 2026-11-16 — Base SKU config moved to `backend/scripts/sku_base.json`; `data/seed/skus.json` is now generated by `build_seed_all.py`. — DATA_SOURCES says skus.json is a merge of base + FoodKeeper + OFF; one hand-edited input, one generated output.
- 2026-11-16 — Bananas and avocados split from a shared `fruit` category into `bananas` / `avocados`. — They have different CO₂e factors (0.86 vs 1.05 kg/kg); categories key CO₂e.
- 2026-11-16 — Added `delivery_every_days` per SKU (bakery + seafood 1, others 2; assumed, same for both stores). Store A par and Store B PO cover one delivery cycle. — With daily delivery for everything, order-up-to never holds stock long enough to waste (Phase 1 finding).
- 2026-11-16 — Added `fresh_picker_share` (both stores): that share of each hour's demand takes the newest units, the rest buy FEFO. — Shoppers picking from the back is a real cause of retail waste; perfect FEFO isn't realistic.
- 2026-11-16 — Calibrated `fresh_picker_share = 0.5`, `store_a_par_mult = 2.0` (spec 1.25), seafood delivered daily: chosen by Store A waste per category vs FAO 2011 retail figures only (Store B results not used). The seafood change was made after seeing Store A seafood at 20.8% vs FAO 9%. — §13/DATA_SOURCES §5 allow global, defensible calibration; no per-seed tuning.
- 2026-11-16 — `base_daily_units` stays illustrative; Favorita supplies dow weights + promo-lift check only. — Family-level medians don't map to individual SKUs; any scaling factor would be arbitrary.
