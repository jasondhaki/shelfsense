# CLAUDE.md — ShelfSense

> Read this file first, every session. Then read `docs/IMPLEMENTATION_PLAN.md` to find the current phase.

## What this project is
**ShelfSense** is a system in the **FoodSphere AI** domain (food-waste reduction in retail). It is a **twin-store retail simulation** with a dark-mode command-center UI. Two stores run side by side on identical shopper traffic over a 7-day (168-hour) cycle:
- **Store A (baseline):** static reorder, printed expiry dates, flat 50% markdown on the last day.
- **Store B (ShelfSense):** weather-adjusted demand, vision-recalibrated shelf life (RSL), elasticity-based dynamic pricing, surplus bundling, and order throttling.

The headline KPI is **simulated waste reduction of Store B vs Store A (target ≥ 30%)**.

The product spec is `docs/PRODUCT_PLAN.md` (the original blueprint, written under the domain name "FoodSphere AI" — the product itself is ShelfSense). Where the build docs and the blueprint disagree, **the build docs win** — they contain deliberate corrections (see `docs/SIMULATION_ENGINE.md` §0).

## Doc map
| File | Read it when… |
|---|---|
| `docs/IMPLEMENTATION_PLAN.md` | Starting any session. Find the current phase and its checklist. |
| `docs/ARCHITECTURE.md` | You need the big picture, repo layout, or a design decision. |
| `docs/SIMULATION_ENGINE.md` | Touching anything in `backend/app/sim/` — the math is specified there exactly. |
| `docs/BACKEND.md` | Writing API routes, WebSocket messages, agents, or Pydantic models. |
| `docs/FRONTEND.md` | Writing UI code. Zones, components, state, design tokens. |
| `docs/DATA_SOURCES.md` | Building seed data or calling NOAA / Open Food Facts / FoodKeeper etc. |
| `docs/AI_PIPELINE.md` | Vision (Gemini) or RAG work. Prompts and JSON schemas live there. |

## Stack (free tiers only — no paid services, ever)
- **Backend:** Python 3.12, FastAPI, Pydantic v2, uvicorn, NumPy. Package manager: `uv`. Tests: `pytest`.
- **Frontend:** React 18 + TypeScript + Vite, Tailwind CSS, Zustand, Recharts, lucide-react.
- **AI:** Google Gemini API free tier (vision + embeddings). Model names come from env vars, never hard-coded.
- **RAG store:** small local vector index (NumPy `.npz`) + BM25 fallback. No hosted vector DB.
- **Hosting (Phase 8):** Vercel (frontend), Render free web service (backend).

## Commands
```bash
# backend
cd backend && uv sync
uv run uvicorn app.main:app --reload --port 8000
uv run pytest -q
uv run python -m app.sim.cli --hours 168 --seed 42      # headless sim run, prints KPIs

# frontend
cd frontend && npm install
npm run dev            # http://localhost:5173, proxies /api and /ws to :8000
npm run typecheck && npm run lint && npm run build
```

## Hard rules
1. **The simulation is deterministic.** Same seed + same event timeline ⇒ identical output. All randomness goes through `app/sim/rng.py`. Never call `random` or `np.random` directly elsewhere.
2. **LLMs never do arithmetic that drives state.** Prices, RSL, POs and KPIs are computed in plain Python from `docs/SIMULATION_ENGINE.md`. The LLM only (a) extracts vision JSON and (b) writes human-readable reasoning text for the log.
3. **The engine is pure.** `app/sim/` has no FastAPI, no I/O, no network, no `asyncio`. It takes state + events and returns new state + log entries. This is what makes it testable.
4. **Every external call has an offline fallback.** NOAA → recorded snapshot. Gemini vision → cached fixture for preset frames. Embeddings → BM25. The demo must run with no API keys and no internet.
5. **Contracts are shared.** If you change a Pydantic model in `backend/app/models/`, update the matching TypeScript type in `frontend/src/types/contracts.ts` in the same change.
6. **Guard every division.** RSL → 0, forecast → 0 and empty inventory are normal states, not crashes. See SIMULATION_ENGINE §7.
7. **Secrets** live in `.env` (git-ignored). `.env.example` lists every variable with a placeholder.
8. **Be honest in the UI.** Values that are assumptions (e.g. elasticity coefficients) are labelled as such in the formula inspector. Don't tune parameters per-seed to hit 30%.

## Conventions
- Python: type hints everywhere, `ruff` for lint + format, dataclasses or Pydantic for state; units in names (`rsl_hours`, `weight_kg`, `price_usd`).
- TypeScript: `strict: true`, no `any`. One component per file. Zone components live in `src/zones/`.
- Time inside the sim is an integer `tick` = simulated hours since Day 1 00:00. Convert to day/hour only for display.
- Money is stored as float USD rounded to cents at display time only.
- Log entries use the agent tags exactly: `VISION_AGENT`, `RAG_KNOWLEDGE_AGENT`, `DEMAND_AGENT`, `PRICING_AGENT`, `PROCUREMENT_AGENT`, plus `SYSTEM`.

## Working style for Claude Code
- Work **one phase at a time**. At the end of a phase: run tests, tick the checklist in `IMPLEMENTATION_PLAN.md`, and summarise what changed.
- Prefer small, reviewable commits with a clear message (`sim: add FEFO sales allocation`).
- When a spec is ambiguous, pick the simplest option consistent with these docs, note it under "Decisions log" in `docs/ARCHITECTURE.md`, and carry on.
- Don't add dependencies without a reason noted in the commit message.
