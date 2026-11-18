# Submission answers — ShelfSense

Ready-to-paste answers for the hackathon form, in the order of `project_submission_scoring_rubric.md`.
Everything here is true of the repository as of 2026-11-18; items marked **TODO (you)** need
information only the team has. Don't claim tools that weren't used.

## 1. Basics

- **Project name:** ShelfSense
- **Elevator pitch:** Twin-store grocery simulation: AI-priced, vision-checked shelves waste 50–58% less perishable food than printed-date stores.
- **Public summary:** ShelfSense runs two grocery stores side by side on the same shoppers and weather for a simulated week. Store A orders and prices by the printed date; Store B uses ShelfSense: weather-adjusted demand, camera-recalibrated shelf life (Gemini vision), elasticity-based markdowns, ethylene-aware surplus boxes and throttled purchase orders. Every decision is logged with its formula and a cited source (USDA FoodKeeper, UC Davis, FAO), and can be explained in plain words by Gemini or a local Ollama model. Over 20 seeds Store B wastes 57.8% ± 8.5 less food; the demo week 50.0% less, 106.6 kg diverted, 150.7 kg CO₂e avoided. English and Bengali UI, light and dark themes, works with no API keys.
- **Domain:** FoodSphere AI (food-waste reduction in retail)
- **Challenge:** **TODO (you)** — the challenge name from the form.
- **Problem statement:** Supermarkets bin perishable food by the printed date, not by its real condition. FAO (2011) estimates North American retail loses up to 12% of fresh fruit and vegetables and 9% of seafood; the date on a pack ignores how it was actually handled (a cold-chain delay, rain-driven humidity, bruising), so stores either discount too late or throw away food that was still good. Ordering is a fixed order-up-to level that ignores weather and weekday demand, so the excess is built in before the week starts. Store managers have no way to see, per product and per hour, how much shelf life is really left, what price would sell it in time, or why a system recommends a markdown — so they don't trust automated pricing.
- **Solution:** A deterministic twin-store simulation with five agents. The Demand agent forecasts hourly sales from Favorita weekday patterns and live/snapshot weather. The Vision agent (Gemini multimodal, structured JSON) grades shelf photos and recalibrates remaining shelf life with an effective-age model. The Pricing agent sizes markdowns to the gap between the velocity needed to sell before expiry and the forecast, with a price floor and hysteresis, and packs leftovers into ethylene-aware Flash Surplus Boxes. The Procurement agent throttles next-delivery orders. The RAG Knowledge agent cites FoodKeeper/UC Davis/USDA AMS/FAO for every event. All numbers are computed in plain Python (LLMs never set prices); an "Explain in plain words" button turns any decision into a cited, number-checked sentence. The UI is a React command centre with live WebSocket updates; MCP servers, a report API and an n8n workflow expose it to other tools.
- **Data lifecycle:** Acquire (scripts download FoodKeeper JSON, Open Food Facts API, Kaggle Favorita CSV, NOAA/Open-Meteo forecasts; raw files cached in git-ignored `data/raw/`) → Parse & clean (pandas aggregates over 4.7 GB Favorita in chunks, unit conversion, hand-picked FoodKeeper records, nulls for missing OFF fields) → Validate (Pydantic schemas in `build_seed_all.py`, fail loudly) → Store (committed seed JSON, RAG corpus Markdown, chunks/BM25/NPZ indexes, knowledge graph JSON; accounts and saved runs in Postgres/SQLite) → Serve (FastAPI REST + WebSocket ticks, MCP tools, `/api/report`) → Analyse (KPIs, 20-seed benchmark, DuckDB/Parquet warehouse) → Deliver (dashboard, CSV export, n8n alerts, CI artifacts) → Retire (guest sessions in memory only, LRU-evicted; raw Kaggle rows never committed).

## 1b. Storage & data

- **Graph DB:** Neo4j (AuraDB Free or local) via `scripts/sync_neo4j.py` (HTTP Query API; loaded into a local Neo4j 5.26 in Docker on 2026-11-18, 59 nodes / 87 relationships, clash query checked); the same graph (`data/rag/graph.json`, 59 nodes / 87 edges) powers graph RAG in-app.
- **Vector DB:** pgvector on Neon Postgres (`scripts/sync_pgvector.py`; 44 chunks synced on 2026-11-18, cosine nearest-neighbour query checked); in-app vector index is NumPy `.npz` (3072-d Gemini embeddings).
- **Lakehouse / warehouse:** DuckDB + Parquet (`scripts/export_warehouse.py`: `runs`, `daily`, `sku_waste` tables).
- **Storage targets:** Neon Postgres (accounts, saved runs, pgvector), SQLite (offline fallback), local files (JSON seed, Markdown corpus, NPZ, Parquet/DuckDB), Neo4j.
- **Storage details:** Accounts use scrypt-hashed passwords and HMAC tokens; a signed-in user's week is stored as (seed, tick, event timeline) and replayed deterministically on load (~0.2 s) instead of storing state. Seed data and indexes are small and committed so the demo has no database dependency.
- **Data sources:** USDA FSIS FoodKeeper (CC0), Open Food Facts (ODbL), Kaggle Corporación Favorita, NOAA api.weather.gov, Open-Meteo, FAO (2011) Annex 4, Poore & Nemecek (2018) via Our World in Data, USDA AMS ethylene report, UC Davis Postharvest Center, Unsplash photos.
- **Source types:** public REST APIs (OFF, NOAA, Open-Meteo), open-data files (FoodKeeper JSON), competition dataset CSV (Kaggle), research publications/PDF (FAO, AMS, UC Davis), images (Unsplash, user uploads/camera).
- **Acquisition methods:** API extraction with caching and a polite User-Agent (`build_seed_off.py`, `snapshot_noaa.py`, `snapshot_open_meteo.py`), bulk file download + chunked parsing (Favorita, FoodKeeper), manual curation from publications (ethylene table, FAO rates), live API at runtime with snapshot fallback (weather widget), image upload.
- **Scrapers / extractors:** Open Food Facts product extractor, NOAA gridpoint forecast extractor, Open-Meteo extractor, FoodKeeper record extractor, Favorita chunked CSV aggregator, Gemini vision extractor (images → JSON).
- **MCP servers for data access:** `shelfsense-warehouse` (SQL over the DuckDB warehouse), `shelfsense-knowledge` (search, graph, credits), `shelfsense-demand` (weather + demand) and `shelfsense-sim` (reports).

## 1c. Parsing, quality, analytics

- **Formats:** JSON, CSV, Markdown with front-matter, JPEG/PNG images, NumPy NPZ, Parquet, DuckDB, PDF sources (cited).
- **Parsers:** pandas (CSV), Pydantic (JSON validation), front-matter Markdown parser, sentence splitter for semantic chunking, Gemini structured output (image → JSON).
- **Formatters / converters:** seed builders normalise FoodKeeper storage periods to hours; CSV export; Parquet export; graph export to Cypher.
- **Cleaning & enrichment:** missing OFF fields → null; FoodKeeper ranges → lower bound; Favorita promo lift computed as a sanity check; chunks enriched with LLM-written context; SKUs enriched with ethylene class, CO₂e factor, Nutri-Score.
- **Schema validation:** Pydantic v2 for seed files, API contracts (mirrored in TypeScript), vision JSON (schema-forced + validated, retry once), event payloads (extra keys rejected).
- **Data quality measures:** `build_seed_all.py` validates every seed record (ranges, required fields) and fails the build; tests check unit conservation (received = sold + wasted + on hand), no negative stock, determinism across runs, guarded divisions; Store A waste is calibrated against FAO retail rates per category; the RAG eval keeps retrieval quality above a floor.
- **Visualization tools:** Recharts (waste/revenue charts, sparklines), custom SVG gauges and bounding-box canvas, DuckDB CLI tables.
- **Dashboards & reports:** 10-tab dashboard (Dashboard, Inventory, Forecast, Pricing, AI Agents, Orders, Analytics, Data Ingestion, Settings, Help), System Architecture modal with live status, CSV report, `/api/report` JSON, weekly CI benchmark artifact.
- **ML / analytics methods:** multimodal vision classification + defect detection (Gemini), demand forecasting (weekday × hour × weather multipliers), price-elasticity optimisation, BM25 + dense-embedding retrieval, Monte-Carlo benchmarking over seeds (common random numbers).
- **Non-AI analytics:** KPIs (waste %, kg diverted, CO₂e avoided, margin recovered), FEFO allocation, order-up-to vs throttled ordering, calibration against FAO, mean ± std over 20 seeds.
- **Insights delivery:** live dashboard over WebSocket, alert bell, agent reasoning log with formulas and citations, plain-language explanations, n8n Slack/Discord message, CSV/Parquet exports.

## 1d. Pipeline, ops, governance

- **Orchestration:** an async `SimController` drives the tick loop; an `Orchestrator` runs agents in a fixed order per tick through an `AgentBus`; GitHub Actions orchestrates CI; n8n orchestrates the daily report.
- **Orchestration details:** Each simulated hour the engine follows a fixed order (SIMULATION_ENGINE §10): apply queued events, update weather, deliveries, camera sweep, Demand agent, Pricing agent, Bundling, sales (FEFO), ageing and waste, Procurement at 21:00, KPIs; the orchestrator adds RAG citations to the log and the controller pushes one delta over the WebSocket, so the run is reproducible from the seed and event timeline alone.
- **Scheduling / triggers:** GitHub Actions on push/PR + weekly cron; n8n schedule (07:00) + webhook trigger; user events (rainstorm, cold-chain, scan) queued to a tick.
- **Streaming / real-time:** WebSocket `/ws/sim` streams one delta per simulated hour (KPIs, shelf labels, chart point, logs, weather), with reconnect and a waking-server overlay; speed up to fast-forward.
- **Outbound APIs:** REST (`/api/sim/*`, `/api/report`, `/api/explain`, `/api/vision/scan`, `/api/meta/architecture`), MCP tools.
- **Webhooks & exports:** n8n webhook trigger + outgoing Slack/Discord webhook, CSV export, Parquet export.
- **Embeddings / model serving:** Gemini embeddings for chunks (batched, one call) and templated queries (cached to `query_cache.npz`, so deployed servers make zero embedding calls); local model serving through Ollama for explanations.
- **Open-source stack:** FastAPI, Pydantic, NumPy, pandas, DuckDB, psycopg, MCP Python SDK, React, Vite, Tailwind, Zustand, Recharts, lucide-react, pytest, ruff, oxlint.
- **Privacy & compliance notes:** No personal data in the simulation. Accounts store email + scrypt hash only; email verified by 6-digit code; tokens revocable; login/sign-up rate limits; no account enumeration on password reset. Kaggle rows are never committed (licence) — only aggregates. Secrets live in `.env`/Render env vars. The public demo sends no images to an AI service unless live vision is switched on.
- **Lineage / observability notes:** Every RAG chunk carries source, title, URL and SKU ids into each citation; seed files record their source and retrieval date (`CREDITS.md`); `context_by` records whether a chunk's context was LLM- or metadata-written. `/api/health` and the architecture modal show which components are live or on fallback; every agent decision is logged with its inputs.
- **Cost & performance:** Free tiers only (Vercel, Render, Neon, Gemini free tier). 168 simulated hours run in ~0.2 s; reports are LRU-cached; vision defaults to cached fixtures on the public demo; templated query embeddings are precomputed; explanations are cached.
- **Other notes:** Determinism is a hard rule — all randomness through one RNG module — which is what makes saved runs, tests and the benchmark reproducible.
- **Publish local environment to internet:** Cloudflare Tunnel (`cloudflared tunnel --url http://localhost:5173`) or ngrok; production on Vercel + Render.
- **Tunneling notes:** The Vite dev server proxies `/api` and `/ws` to the backend, so one tunnel to port 5173 serves the whole app including the WebSocket; `vite.config.ts` allows `*.trycloudflare.com` and `*.ngrok-free.app` hosts.

## 2. AI

- **LLMs / models:** Google Gemini (`GEMINI_VISION_MODEL`, set to `gemini-3.5-flash-lite` here) for vision and explanations; `gemini-embedding-001` for embeddings; local open-weight models for explanations, each pulled and run on 2026-11-18 with answers that passed the number guardrail: Qwen2.5 3B Instruct (`qwen2.5:3b`), DeepSeek-R1 Distill Qwen 1.5B (`deepseek-r1:1.5b`), Llama 3.2 3B (`llama3.2:3b`), Gemma 3 1B (`gemma3:1b`).
- **LLM usage commentary:** LLMs extract (image → JSON) and explain (decision → sentence); they never compute prices, shelf life or orders (hard rule). Both are behind offline fallbacks.
- **Prompt strategy:** see `docs/PROMPT_LIBRARY.md` — schema-forced JSON with closed vocabularies for vision; grounded, cite-your-source, no-arithmetic prompt for explanations; Anthropic's contextual-retrieval prompt for chunk headers; fixed query templates.
- **Token optimization:** log data trimmed to 1,200 chars; top 3–4 chunks of ~250 chars; output caps; temperature 0; answer cache keyed by input; query embeddings precomputed and committed; embeddings in one batched call; LLM chunk contexts reused while text is unchanged; images resized to ≤ 1024 px; vision cached on the public demo.
- **RAG techniques:** hybrid-capable retrieval (BM25 + dense vectors, auto fallback), metadata filtering by SKU and source, contextual retrieval (LLM-written chunk context), semantic variable-size chunking, graph RAG (knowledge-graph facts + multi-hop expansion over ethylene clashes), query templating/caching, labelled retrieval eval.
- **RAG architecture:** corpus Markdown with front-matter → semantic chunks → context sentence per chunk → BM25 tokens + Gemini embeddings (`index.npz`) + knowledge graph (`graph.json`) → `Retriever` (filter by SKU/source, score, deterministic tie-break) → agents cite hits in the log; explanations combine graph facts with graph-expanded hits.
- **Local runtimes:** Ollama 0.40.16 (`LLM_PROVIDER=ollama`) and llama.cpp `llama-server` build 12457 (`LLM_PROVIDER=openai_compat`, OpenAI-compatible API; also fits LM Studio/vLLM). Both verified 2026-11-18 on the same pricing and ethylene-clash log lines: every answer came back in mode `llm` and passed the guardrail.
- **Hardware / quantization:** CPU-only laptop — Intel Core i7-10610U (4 cores, 1.8 GHz), 16 GB RAM, Intel UHD integrated graphics, no CUDA. All models are GGUF Q4_K_M (Ollama default tags; ~0.8–2 GB); llama.cpp loaded the same Qwen2.5-3B Q4_K_M GGUF with a 4,096-token context. One explanation takes ~20–65 s on this CPU (Gemini: ~2 s). Small models sometimes misread the formula (e.g. calling velocity a temperature) — the guardrail checks numbers, not meaning — so Gemini stays the hosted default and local models are the offline/private option.
- **Agentic framework / orchestration notes:** a custom, deterministic multi-agent design (five agents + orchestrator + bus) rather than an LLM-driven framework, because state-changing decisions must be reproducible; MCP exposes the agents' capabilities to external agent hosts (Claude Code / Claude Desktop). Claude Code was the development agent.
- **Frontend / visual AI builders:** Claude Code (built the UI from the team's image mock-ups). **TODO (you):** add any others actually used (e.g. v0, Lovable, Figma AI).
- **Workflow automation:** n8n (`automation/n8n/shelfsense_daily_report.json`; imported and executed in n8n on 2026-11-18 against the live Render API, retries cover Render's cold start), GitHub Actions (`.github/workflows/ci.yml`, passing).
- **AI-DLC process notes:** Spec-first: a product blueprint, then build docs (architecture, simulation maths, backend, frontend, data, AI pipeline) that override the blueprint where they correct it. `CLAUDE.md` holds the hard rules every session reads first. Work proceeded in nine phases, each with a kickoff prompt, a checklist and acceptance checks (tests, CLI timings, benchmark numbers) recorded in `docs/IMPLEMENTATION_PLAN.md`; ambiguities were resolved by the simplest option and logged in the ARCHITECTURE decisions log (one dated line each). Tests were written alongside or before engine code; numbers were never tuned per seed to hit the target.
- **MCP servers built (5):** `shelfsense-sim`, `shelfsense-knowledge`, `shelfsense-vision`, `shelfsense-demand`, `shelfsense-warehouse` (stdio + streamable HTTP). Tools: `run_week`, `benchmark`, `list_skus`, `price_formula`; `search_knowledge`, `product_graph`, `explain_decision`; `list_frames`, `grade_frame`, `grade_image`; `weather_now`, `demand_forecast`; `tables`, `query`. Resources `shelfsense://credits`, `shelfsense://graph`. Permissions: read-only — no tool changes a running session; the warehouse connection is DuckDB read-only with external file access disabled and accepts one SELECT/WITH only; `grade_image` accepts JPEG/PNG ≤ 5 MB; HTTP binds to 127.0.0.1.
- **MCP servers used / clients:** Claude Code is the MCP host (`.mcp.json`). **TODO (you):** list other MCP servers you used while building (e.g. a browser or Vercel/Render server) only if you did.
- **MCP reuse notes:** all five servers reuse the app's own modules (`reports.week_report`, `Retriever`, `explain`, the vision fixtures and α formula, the demand model, the weather services, the warehouse export) so MCP answers match the API and UI exactly.
- **Fine-tuning / adaptation:** none — adaptation is by retrieval (RAG), prompt design and a hand-reviewed fixture set; vision fixtures were generated live then reviewed.
- **Evaluation:** retrieval eval on 30 labelled queries (hit@3, MRR; BM25 contextual 0.967 / 0.916, plain 1.0 / 0.839, vector 1.0 / 0.983); vision replies schema-validated; the simulation is evaluated over seeds 1–20 (57.8% ± 8.5) and calibrated against FAO; 90 backend tests in CI.
- **Guardrails / safety / privacy:** LLMs can't change state; vision output schema-validated with fallback; explanation answers rejected if they contain a number not in the context; snippets marked as non-instructions; upload size/type checks (5 MB, JPEG/PNG magic bytes); request-size cap; rate limits on auth; offline mode never sends data out.
- **Open-source AI tools:** google-genai SDK, MCP Python SDK, Ollama, llama.cpp, open-weight Qwen2.5 / DeepSeek-R1 / Llama 3.2 / Gemma 3, DuckDB, NumPy BM25/vector retriever (own code).

## 3. Links

- **GitHub:** **TODO (you)** — the repo URL.
- **Live demo:** https://shelfsense-tau.vercel.app
- **Other links:** API health https://shelfsense-api-66nh.onrender.com/api/health
- **YouTube / Figma:** **TODO (you).**

## 4. Build provenance

- **Tooling / IDE:** Claude Code (CLI). **TODO (you):** your editor.
- **Frameworks & libraries:** FastAPI, Pydantic v2, NumPy, React 18, TypeScript, Vite, Tailwind, Zustand, Recharts.
- **Deployment:** Vercel (frontend), Render Blueprint `render.yaml` (backend), Neon (Postgres).
- **Context / memory files:** `CLAUDE.md`, `docs/*.md` (spec + decisions log), `docs/PROMPT_LIBRARY.md`.
- **MCP servers list / tools / permissions:** see section 2.

## 5. Team

**TODO (you).**
