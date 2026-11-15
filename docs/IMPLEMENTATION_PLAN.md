# Implementation Plan — ShelfSense

Nine phases. Each one ends with something that runs and is tested. Don't start a phase until the previous phase's acceptance checks pass.

**Current phase:** `Phase 2 (waiting on FoodKeeper + Favorita raw files)` ← update this line when a phase is done.

| Phase | Goal | Rough effort |
|---|---|---|
| 0 | Repo scaffold, tooling, contracts skeleton | 0.5 day |
| 1 | Pure simulation engine + CLI, fully tested | 2–3 days |
| 2 | Real seed data from the five sources | 1–2 days |
| 3 | FastAPI: controller, agents, REST + WebSocket | 1–2 days |
| 4 | Frontend shell + Zones A, C, E live | 2 days |
| 5 | Zone D (procurement + bundles) + chart + formula drawer | 1–2 days |
| 6 | Vision pipeline + Zone B | 1–2 days |
| 7 | RAG knowledge agent + citations | 1 day |
| 8 | Architecture modal, polish, deploy, demo script | 1–2 days |

How to use this with Claude Code: at the start of each phase, paste that phase's **Kickoff prompt**. At the end, ask Claude Code to run the acceptance checks, tick the boxes and update **Current phase**.

---

## Phase 0 — Scaffold
**Kickoff prompt:**
> Read CLAUDE.md and docs/ARCHITECTURE.md. Do Phase 0 from docs/IMPLEMENTATION_PLAN.md: create the repo layout, backend with uv + FastAPI + pytest + ruff, frontend with Vite React TS + Tailwind + Zustand + Recharts, the .env.example, and a /api/health endpoint the frontend can call through the Vite proxy. Don't implement any simulation logic yet.

- [x] `git init`, `.gitignore` (Python, Node, `.env`, `backend/data/raw/`)
- [x] Copy the original blueprint to `docs/PRODUCT_PLAN.md` (already included)
- [x] `backend/pyproject.toml` (fastapi, uvicorn[standard], pydantic, pydantic-settings, numpy, httpx; dev: pytest, ruff)
- [x] `app/main.py` with CORS from env, `/api/health`
- [x] `app/config.py` (pydantic-settings) + `.env.example` from BACKEND §2
- [x] Empty packages: `sim/ agents/ services/ rag/ models/ api/`
- [x] `frontend/` Vite React TS, Tailwind with the tokens from FRONTEND §2, Inter + JetBrains Mono
- [x] Vite proxy: `/api` and `/ws` → `localhost:8000`
- [x] `App.tsx` renders the 5-zone grid with placeholder panels and the health status
- [x] `tests/test_health.py`, `tests/test_imports.py` (sim isolation rule)

**Acceptance:** `uv run pytest` green · `npm run build` green · opening `localhost:5173` shows the empty 5-zone layout and "backend: ok".

---

## Phase 1 — Simulation engine (the heart)
**Kickoff prompt:**
> Read CLAUDE.md and docs/SIMULATION_ENGINE.md carefully. Do Phase 1: implement backend/app/sim/ exactly as specified — state dataclasses, rng with common random numbers, shelf_life (effective-age model), demand, pricing, bundling, procurement, events, kpi, engine.step following the tick order in §10, and cli.py. Write tests for every row of §12 plus unit-conservation and determinism tests first, then implement until they pass. No FastAPI imports in app/sim.

- [x] `state.py` — `SkuConfig`, `SimConfig`, `Batch`, `StoreState`, `SimState`, `Box`
- [x] `skus.json` with the illustrative table (§2) + assumed `hour_share` + flat `dow_weight`
- [x] `rng.py` — `uniform(seed, stream, *keys)` via `np.random.default_rng([seed, stream_id, *keys])`; `poisson_inv_cdf`
- [x] `shelf_life.py` — age update, RSL true/known, inspection, α from quality score (AI_PIPELINE §1.3)
- [x] `demand.py` — λ, horizon forecast, price multiplier, realised demand
- [x] `pricing.py` — FEFO V_target, ΔQ/ΔP, floor, hysteresis, Store A rule
- [x] `bundling.py` — trigger, greedy box building, box sales, expiry
- [x] `procurement.py` — Store A order-up-to, Store B throttled PO, PO rows
- [x] `events.py` — rainstorm, cold-chain (next delivery + immediate), vision_override
- [x] `kpi.py` — all KPIs from §9 + chart point
- [x] `engine.py` — `step(state, queued_events) -> (state, list[LogDraft])`
- [x] `cli.py` — `--hours --seed --scenario {none,demo}`; prints a per-day table and final KPIs
- [x] Tests: §12 vectors, conservation of units, no negative stock, determinism, edge cases §11
- [x] Run seeds 1–20 (no events) and the demo scenario; paste results below

**Acceptance:** all tests green · CLI < 2 s for 168 h · results recorded:

```
Phase 1 results (2026-11-16, spec parameters from §2, store_a_par_mult = 1.25):
  No events, seeds 1–20: waste reduction undefined — Store A wastes 0 kg on every seed
    (Store B 0 kg on 19/20; 0.9 kg on seed 20). Net margin recovered ≈ $240–330 (B carries less stock).
  Demo scenario, seed 42: waste reduction = — (A 0 kg, B 0 kg), food diverted = 0 kg, margin recovered = $284.69
  CLI: 168 h in ~0.2 s. 27 tests green (all §12 vectors, conservation, determinism, §11 edges).
  Parameter changes made (and why): none yet — see "Calibration open" below.

  Calibration open: with the §2 parameters the baseline cannot produce waste. Order-up-to replaces
  exactly what sold (≤1.25 days of stock, so nothing gets near 48 h), and the 50% last-day markdown
  multiplies the whole SKU's demand by ~2×, clearing any old units. Probes (seeds 1–20):
    par 2.0 → A waste 0.0%; par 3.0 → 0.3%; par 4.0 → 3.1% (reduction ≈ 94–99%, not credible)
    + daily demand overdispersion (CV 0.3–0.4) → still ≈ 0%
    + 30–50% of shoppers picking the freshest unit → still ≈ 0%
  Needs a modelling decision before Phase 2 calibration against FAO retail waste.
```

---

## Phase 2 — Real data
**Kickoff prompt:**
> Read docs/DATA_SOURCES.md. Do Phase 2: write the scripts in backend/scripts/ to build seed files from USDA FoodKeeper, Open Food Facts, Favorita aggregates, NOAA snapshot and FAO retail waste, plus build_seed_all.py with schema validation. Verify each source's current URL/fields before coding against it. I will download the Kaggle and FoodKeeper raw files into backend/data/raw/ myself — tell me exactly which files you need.

- [x] `build_seed_foodkeeper.py` → `foodkeeper.json` + RAG corpus files — written + unit-tested; **not yet run on real data** (needs manual download, FSIS returns 403 to scripts)
- [x] `build_seed_off.py` → OFF fields merged into `skus.json`
- [x] `ethylene.json` (hand-curated, cited)
- [x] `build_seed_favorita.py` → `sales_profile.json` (aggregates only) — written + tested on synthetic data; **not yet run on real data** (needs Kaggle download)
- [x] `snapshot_noaa.py` → `weather_snapshot.json`
- [x] `faostat.json` with sources for every number
- [x] `build_seed_all.py` + Pydantic validation
- [x] `data/seed/CREDITS.md`
- [ ] Re-run Phase 1 benchmark with real data; record results; check Store A waste vs FAO retail range — done with OFF/NOAA/FAO; **re-run after FoodKeeper + Favorita land**

**Acceptance:** `build_seed_all.py` passes validation · tests still green · CREDITS.md complete · new benchmark recorded:

```
Phase 2 results (2026-11-16; OFF + NOAA snapshot + FAO + OWID merged; FoodKeeper SL and Favorita dow PENDING):
  Calibration (seeds 1–20, no events) — chosen only on Store A vs FAO, Store B not looked at:
    swept fresh_picker_share {0.3, 0.5, 0.7} × store_a_par_mult {1.25, 1.5, 2.0} → best 0.5 / 2.0
    then seafood delivery set to daily (was every 2 days: Store A seafood 20.8% vs FAO 9%)
  Store A / Store B waste % of units received, vs FAO 2011 NA retail:
    berries 12.0 / 0.7 (FAO 12) · avocados 11.4 / 0.5 (12) · leafy_greens 10.9 / 0.3 (12)
    vegetables 8.9 / 0.0 (12) · bananas 8.8 / 0.1 (12) · seafood 2.1 / 0.2 (9)
    bakery 1.0 / 0.1 (2) · dairy 0.1 / 0.0 (0.5)
  No-event waste reduction, seeds 1–20: 98.0% ± 1.4
  Demo scenario, seed 42: reduction 93.9%, diverted 220.0 kg, CO2e 390.8 kg, margin recovered $2,331.60

  Store B looked implausibly good (≈0.1–0.7% waste, margin $2,331 inflated by Store A's closing stock).

  Update 2026-11-16 — added forecast error (day-level demand shock, CV 0.3, unseen by Store B's
  forecast) + closing-stock credit in GM; recalibrated (best fit unchanged: 0.5 / 2.0, |A−FAO| 1.7 pp):
    Store A / Store B waste %: berries 14.6 / 2.7 · avocados 12.6 / 2.3 · leafy_greens 11.4 / 1.5
      bananas 9.6 / 0.3 · vegetables 9.6 / 0.5 · seafood 5.0 / 0.8 · bakery 2.5 / 0.9 · dairy 1.0 / 0.0
    No-event waste reduction, seeds 1–20: 92.7% ± 6.9
    Demo scenario, seed 42: reduction 93.1%, diverted 227.6 kg, CO2e 362.6 kg, margin recovered $696.85
    Trade-off now visible: Store B sells ~6% fewer units (lean stock → stock-outs), revenue $11.6k vs $12.5k.
  Remaining known optimism: price cuts create demand with no pull-forward from later hours.
```

---

## Phase 3 — Backend API, controller, agents
**Kickoff prompt:**
> Read docs/BACKEND.md. Do Phase 3: Pydantic contracts in app/models, SimController with an asyncio loop (play/pause/fast_forward/step/reset), event queue, agents + orchestrator + AgentBus producing LogEntry objects per the logging rules, NOAA service with snapshot fallback, REST routes and the /ws/sim WebSocket. Vision and RAG agents can be stubs that log "not yet implemented". Write the API tests.

- [ ] `models/` contracts from BACKEND §5
- [ ] `agents/bus.py`, `orchestrator.py`, demand/pricing/procurement/bundling agents (log templates)
- [ ] `controller.py` — single SimState, speed control, stop at tick 168, replay
- [ ] `services/noaa.py` with cache + fallback
- [ ] REST routes (BACKEND §3) incl. `/sim/skus/{id}/formula`
- [ ] WebSocket `hello` / `tick` / `status` / `event_applied`, ping/pong
- [ ] `tests/test_api.py` (TestClient, uses `step` — no sleeping)

**Acceptance:** tests green · `websocat ws://localhost:8000/ws/sim` (or a tiny script) shows ticks after `POST /api/sim/control {"action":"play"}` · a rainstorm event produces DEMAND + PRICING + PROCUREMENT log lines.

---

## Phase 4 — Frontend shell, Zones A, C, E
**Kickoff prompt:**
> Read docs/FRONTEND.md. Do Phase 4: contracts.ts mirroring the backend models, the Zustand store, the WebSocket client with reconnect and the waking-server overlay, then build Zone A (controls, clock, weather, event buttons, KPI cards), Zone C (8 ESL cards) and Zone E (agent log with filters). Zones B and D stay as placeholders.

- [ ] `types/contracts.ts`, `lib/api.ts`, `lib/ws.ts`, `store/simStore.ts`
- [ ] `TelemetryBar` + `KpiCard`
- [ ] `EslMatrix` + `EslCard` (bar, RSL countdown, price flash, state ribbon)
- [ ] `AgentLog` (auto-scroll, filters, expandable data)
- [ ] Waking-server overlay

**Acceptance:** typecheck/lint/build clean · press Play → clock advances, ESL prices change, log streams · Fast-forward reaches D7 23:00 and stops · Rainstorm button shows countdown and new log lines.

---

## Phase 5 — Zone D, chart, formula drawer
**Kickoff prompt:**
> Do Phase 5 from docs/IMPLEMENTATION_PLAN.md: Zone D with the Procurement PO table and Flash Surplus Bundles tab, the Store A vs Store B cumulative waste chart, and the FormulaDrawer that opens when an ESL card is clicked (uses /api/sim/skus/{id}/formula).

- [ ] `ExecutionModules` with both tabs + empty states
- [ ] PO rows highlight when changed by weather
- [ ] Bundle cards with expiry countdown and status
- [ ] Recharts waste comparison chart
- [ ] `FormulaDrawer` with step-by-step numbers and "assumed" label on ε

**Acceptance:** in a fast-forward run you can see at least one bundle created and sold/expired · PO table changes after a rainstorm · formula drawer numbers match the CLI for the same tick (spot-check one SKU).

---

## Phase 6 — Vision + Zone B
**Kickoff prompt:**
> Read docs/AI_PIPELINE.md §1. Do Phase 6: services/gemini.py using the google-genai SDK with structured output, the VisionAgent with cached/live modes and fallbacks, POST /api/vision/scan, the alpha mapping, and the SmartCamInspector zone with frame carousel, upload dropzone, BoundingBoxCanvas and the result panel. Then help me generate and hand-correct the three fixture files.

- [ ] Source 3 preset images + `CREDITS.md`
- [ ] `services/gemini.py` (timeout, 1 retry, schema validation)
- [ ] `vision_agent.py` + `/api/vision/scan` (preset/upload, size/type checks)
- [ ] Fixtures `frame1..3.json` generated live, then reviewed
- [ ] `SmartCamInspector` + `BoundingBoxCanvas` (0–1000 coords) + result panel + mode badge
- [ ] Scan queues `vision_override`; ESL card for that SKU reacts next tick
- [ ] Tests: fixture path, invalid upload, Gemini failure → fallback

**Acceptance:** with `VISION_MODE=cached` and no key, Frame 3 scan draws red boxes, shows RSL drop, strawberries' price falls within 1–2 ticks · with a key and `live`, a custom upload returns boxes or a friendly error.

---

## Phase 7 — RAG knowledge agent
**Kickoff prompt:**
> Read docs/AI_PIPELINE.md §2. Do Phase 7: build_rag_index.py (vector + BM25), app/rag/retriever.py with mode auto/vector/bm25, and the RAG_KNOWLEDGE_AGENT wired into vision scans, cold-chain, humidity events and bundling (ethylene warnings). Citations appear in the log data and the vision result panel.

- [ ] Corpus complete (FoodKeeper, OFF, ethylene, humidity, FAO)
- [ ] `index.npz`, `chunks.json`, `bm25.json` committed
- [ ] `retriever.py` + query cache
- [ ] Agent hooks + log format
- [ ] Ethylene check in bundling (producer + sensitive in one box → warn and swap if possible)
- [ ] Tests: BM25 mode returns the FoodKeeper strawberry chunk for the strawberry query

**Acceptance:** with no key, every vision scan and event shows a cited source in Zone E.

---

## Phase 8 — Polish, deploy, demo
**Kickoff prompt:**
> Do Phase 8: the System Architecture modal with live node status, accessibility and reduced-motion pass, README with setup and screenshots, deploy the backend to Render (free) and the frontend to Vercel, and a scripted demo mode. Walk me through the deploy steps that need my accounts.

- [ ] `ArchitectureModal` + `/api/meta/architecture`
- [ ] Reduced motion, focus rings, aria labels, colour + icon severity
- [ ] `README.md` (what it is, screenshot/GIF, run locally, data credits, limitations)
- [ ] `render.yaml` or documented Render settings; Vercel env vars
- [ ] Demo preset: `POST /api/sim/control {"action":"reset","scenario":"demo"}` loads the scripted timeline
- [ ] Final benchmark recorded below

**Acceptance:** public URLs work from a fresh browser · cold start handled gracefully · the 3-minute demo below runs without touching a terminal.

---

## Demo script (≈ 3 minutes)
1. **0:00** — "Two identical stores, same shoppers, same weather. Left logic is how most stores work today; right is ShelfSense." Point at the KPI cards (all zero).
2. **0:20** — Play. Watch ESL prices drift on short-life items (sourdough, salmon) while Store A keeps full price. Log shows PRICING_AGENT reasoning with numbers.
3. **0:50** — Trigger **Rainstorm**. Show DEMAND (traffic −22%), PRICING (extra markdowns) and PROCUREMENT (tomorrow's POs cut) log lines; open the PO tab — "Waste Prevention Delta".
4. **1:30** — Zone B: scan **Frame 3**. Red boxes, quality 3.8, RSL 72 h → ~19 h, FoodKeeper citation. Strawberry ESL drops next tick; click it to open the formula drawer.
5. **2:10** — Fast-forward. A **Flash Surplus Mystery Box** appears in the Bundles tab and sells.
6. **2:40** — End of Day 7: final waste reduction %, kg diverted, CO₂e, margin recovered. Open **System Architecture**. Close with the honest caveat: simulated store, assumed elasticities, sources credited.

---

## Results log
```
Phase 1: engine complete; baseline waste ≈ 0 with spec parameters (calibration open)
Phase 2: Store A calibrated to FAO retail ranges; no-event reduction 92.7% ± 6.9 with forecast error (pending FoodKeeper + Favorita)
Final (deployed build, demo scenario seed 42): waste reduction __%, diverted __ kg, CO₂e __ kg, margin $__
```

## Backlog (after Phase 8, only if time allows)
- Per-session simulations (client id → its own SimState)
- Side-by-side Store A vs B ESL toggle
- Export run report (CSV of the hourly series)
- Open-Meteo provider for a Dhaka store location
- Constant-elasticity demand model as an alternative to linear (compare results)
