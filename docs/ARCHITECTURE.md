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
- 2026-11-16 — Added a day-level demand shock per SKU (Gamma, mean 1, `demand_daily_cv = 0.3`, assumed), shared by both stores via CRN and unseen by every forecast. — Without it Store B's forecast equalled true demand (an oracle), giving ≈98% reduction; real day-level fresh forecasts carry roughly 20–40% error.
- 2026-11-16 — Gross margin uses COGS = goods received − closing stock at cost (spec §9 had no closing-stock credit). — Store A's larger end-of-week stock was counted as pure loss, inflating "net margin recovered" (from $697 to $2,332 on the demo).
- 2026-11-16 — FoodKeeper records hand-picked per SKU (`sku_base.json → foodkeeper.{id, field}`) instead of keyword matching; DOP_* ("from date of purchase") columns accepted. — Keyword matching picked muffins for bananas and croutons for sourdough. Milk #27 only says "Package use-by date", so it keeps 144 h (cited).
- 2026-11-16 — Final calibration with all real data: `fresh_picker_share = 0.7`, `store_a_par_mult = 1.5` (re-swept on Store A vs FAO only; supersedes 0.5 / 2.0). Cherry tomatoes (FoodKeeper pantry 10 d) can't reach FAO's 12% in a 7-day run; accepted rather than shortening a sourced shelf life.
- 2026-11-16 — DEMAND / PRICING / PROCUREMENT / bundling log templates stay in `app/sim` next to their math; `agents/orchestrator.py` adapts engine `LogDraft`s to `LogEntry` via `AgentBus` and adds knowledge agents (RAG stub now). No per-agent wrapper classes. — A wrapper per agent would only re-route the same data; keeping text beside the number means a message can't disagree with what it explains.
- 2026-11-16 — Live NOAA only feeds the header widget (`WeatherNow`); the simulation always uses the committed `weather_snapshot.json`. — Determinism (rule 1); DATA_SOURCES §4 "live mode is a toggle" left for later.
- 2026-11-16 — WebSocket handler uses an anyio task group (push + pull), not `asyncio.TaskGroup`. — Starlette cancels apps via anyio cancel scopes; asyncio.TaskGroup surfaced that as CancelledError on disconnect.
- 2026-11-16 — A second rainstorm while one is active, events after tick 167, and unknown cold-chain SKUs return 409 with the error envelope. — The UI disables these buttons; the API enforces it too.
- 2026-11-16 — Reset uses an inline confirm in the telemetry bar, not `window.confirm`. — Native dialogs block the page (and browser automation); FRONTEND §4 only asks for a confirmation.
- 2026-11-16 — ESL surplus text reads "N won't sell within 24 h", not "at risk of waste". — §5.2 `surplus_risk_units` is stock beyond the next 24 h of sales; for long-life items (milk, 139 h) it is not waste risk (rule 8, honest UI).
- 2026-11-16 — The 21:00 PO log line is stamped with the tick it was computed in (was the next hour). — The PO uses `from_tick = t+1` for "first unsold hour"; the log time should be 21:00.
- 2026-11-16 — Waste chart: Store A line `#7C8BA1` (token `chart-a`), dashed; Store B accent `#38BDF8`. — The spec's `baseline #94A3B8` vs accent failed the dataviz validator on the panel surface (normal-vision ΔE 11.6 < 15). `#7C8BA1` passes (ΔE 16.1, CVD 13.9, contrast ≥ 3:1); dashing + legend + direct end labels + table view mean colour is never the only cue.
- 2026-11-16 — Formula drawer refetches `/sim/skus/{id}/formula` on every tick while open and shows "computed D… HH:00". — The breakdown is the decision of the previous tick; refreshing keeps it in step with the live price.
- 2026-11-16 — Zone D shows the waste chart beside the tabs (not a third tab). — FRONTEND §4 allows either; side-by-side keeps the headline comparison always visible.
- 2026-11-16 — Preset frames live in `frontend/public/frames/` (not `src/assets/frames/`) and the browser sends the image bytes with every scan (resized to ≤ 1024 px JPEG client-side). — One copy of each image; live mode can analyse presets without the backend holding images; no Pillow on the server.
- 2026-11-16 — Bounding boxes are absolutely positioned elements over the `<img>` in % of the 0–1000 grid, not a `<canvas>`. — Same result, crisp at any size, and the labels stay real text for screen readers.
- 2026-11-16 — Draft vision fixtures were hand-written from the downloaded frames; Frame 3 uses mold + soft_spots + leakage (α 2.5) instead of the spec's "ethylene_bruising". Frame 2 shows bananas only (targets BANA-01, α 1.46). — No key yet; ethylene bruising isn't visible on a strawberry. Regenerate live and review when a key is set.
- 2026-11-16 — Until Phase 7, the RAG agent logs the FoodKeeper record found by direct lookup for vision scans, labelled "direct lookup". — Citation is real and honest; vector/BM25 retrieval replaces it in Phase 7.
- 2026-11-16 — Added `google-genai` (spec'd vision SDK) and `python-multipart` (FastAPI form/file uploads).
- 2026-11-16 — BM25 implemented in ~20 lines in `app/rag/retriever.py` instead of the `rank-bm25` package. — Corpus is 35 chunks; Okapi BM25 is a few lines and avoids a dependency. `bm25.json` still stores the tokenised corpus as specified.
- 2026-11-16 — Vector mode embeds every templated query once at startup (`Retriever.warm`); inside a tick any uncached query uses BM25. — Retrieval runs in the synchronous tick; it must never wait on the network or burn free-tier quota per tick.
- 2026-11-16 — RAG queries use plain produce nouns (`NOUN` map) and knowledge sources only (no Open Food Facts metadata). — Full product names made barcode-metadata chunks outrank handling guidance.
- 2026-11-16 — Box building swaps away from producer+sensitive pairs; a clash is accepted only when the box would otherwise fall below 2 units, and is flagged (warn) with a citation. — AI_PIPELINE §2.4 "warn and swap if possible", without forcing clashes just to fill a third slot.
- 2026-11-16 — Architecture modal uses the native `<dialog>` (`showModal`) and lists nodes by layer with "→ feeds" text instead of drawn SVG edges; agents pulse when they logged on the latest tick. — Native focus trap/Esc/backdrop; the flow reads the same and stays accessible text.
- 2026-11-16 — `WasteChart` is lazy-loaded. — Recharts was 368 kB of a 566 kB bundle; the main bundle is now 198 kB.
