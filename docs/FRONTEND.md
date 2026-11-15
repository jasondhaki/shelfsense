# Frontend Specification — ShelfSense

React 18 + TypeScript (strict) + Vite + Tailwind + Zustand + Recharts + lucide-react. Single screen, dark mode, desktop-first (min width 1280 px). Below 1280 px, zones stack vertically — it doesn't need to be beautiful on mobile, just usable.

## 1. Layout (CSS grid)

```
┌──────────────────────────────── Zone A: Telemetry & Controls (full width) ───────────────────────────────┐
│ [▶ 1x][⏩][⏸][↺]  D3 14:00 ▓▓▓▓▓░░░ 62/168   [🌧 Rainstorm][❄ Cold-chain]   KPI KPI KPI  [System Arch] │
├──────────────────────┬─────────────────────────────────────────────────────┬─────────────────────────────┤
│ Zone B               │ Zone C: ESL Matrix (4 × 2 cards)                    │ Zone E                      │
│ Smart-Cam Inspector  │                                                     │ Agent Reasoning Log         │
│ (≈ 340 px)           ├─────────────────────────────────────────────────────┤ (≈ 380 px, full height,     │
│                      │ Zone D: [Procurement POs] [Flash Bundles] + chart   │  auto-scroll, filterable)   │
└──────────────────────┴─────────────────────────────────────────────────────┴─────────────────────────────┘
```
`grid-template-columns: 340px 1fr 380px; grid-template-rows: auto 1fr auto;` Zone E spans rows 2–3.

## 2. Design tokens (`tailwind.config.ts` → `theme.extend`)

| Token | Value | Use |
|---|---|---|
| `bg` | `#0B0F14` | page |
| `panel` | `#121821` | zone background |
| `panel-2` | `#1A2230` | cards |
| `line` | `#253043` | borders, dividers |
| `text` | `#E6EDF3` | primary text |
| `muted` | `#8B98A9` | labels |
| `ok` | `#22C55E` | optimal / Store B good |
| `warn` | `#F59E0B` | accelerated ripening / surplus risk |
| `crit` | `#EF4444` | clearance required / waste |
| `accent` | `#38BDF8` | interactive, Store B line |
| `baseline` | `#94A3B8` | Store A line |

Fonts: `Inter` for UI, `JetBrains Mono` for numbers, timers, and the log. Use `tabular-nums` on every changing number so digits don't jitter.

Agent tag colours in the log: VISION violet `#A78BFA`, RAG teal `#2DD4BF`, DEMAND sky `#38BDF8`, PRICING amber `#F59E0B`, PROCUREMENT lime `#A3E635`, SYSTEM muted.

## 3. State (`src/store/simStore.ts`, Zustand)

```ts
interface SimStore {
  connection: 'connecting' | 'waking' | 'open' | 'closed';
  snapshot: SimSnapshot | null;         // last full state
  logs: LogEntry[];                     // ring buffer, keep last 500
  logFilter: Set<AgentName>;
  selectedSku: string | null;           // opens formula drawer
  formula: FormulaBreakdown | null;
  vision: { frameId: FrameId | 'custom' | null; result: VisionScanResult | null; scanning: boolean; error?: string };
  activeTab: 'procurement' | 'bundles';
  // actions
  applyHello(s: SimSnapshot): void;
  applyTick(msg: TickMessage): void;    // merges delta into snapshot, appends logs
  control(action: ControlAction): Promise<void>;
  triggerEvent(type: EventType, payload?: object): Promise<void>;
  scan(frame: FrameId | File): Promise<void>;
  openFormula(skuId: string): Promise<void>;
}
```

`lib/ws.ts`: connect to `VITE_WS_URL` (default `/ws/sim` via Vite proxy), exponential backoff reconnect (1, 2, 4, 8 s… max 15 s). On reconnect, the server's `hello` replaces the snapshot. While `/api/health` hasn't answered for > 3 s, show a "Waking the simulation server…" overlay (Render free tier cold start).

## 4. Zones

### Zone A — `TelemetryBar.tsx`
- **Brand:** "ShelfSense" wordmark at the far left with a small muted subtitle "a FoodSphere AI system". Browser tab title: `ShelfSense — Retail Waste Command Center`.
- **Playback:** Play (1x), Fast-forward, Pause, Reset (confirm dialog: "Reset to Day 1? Current run will be lost."), and a small Step button for debugging (hidden behind `?debug=1`).
- **Clock:** `D{day} {HH}:00` and a progress bar `tick / 168`.
- **Weather widget:** temperature, RH, precip chance, source badge `NOAA live` / `NOAA snapshot`.
- **Chaos injectors:** two buttons. Disabled while the event is active, with a countdown chip ("Storm: 7h left"). Cold-chain opens a tiny popover to pick SKUs (default strawberries/spinach/salmon) and "next delivery" vs "inject now".
- **KPI cards** (`KpiCard.tsx`): Waste Reduction % (target line at 30%; green when ≥ 30), Food Diverted kg (+ CO₂e sub-label), Net Margin Recovered $. Animate number changes (count-up ≤ 300 ms).
- **System Architecture** button → `ArchitectureModal.tsx`.

### Zone B — `SmartCamInspector.tsx`
- Header `CAM-04: FRESH PRODUCE AISLE — BAY 2` with a blinking red REC dot and the sim timestamp.
- Frame carousel: Frame 1, 2, 3 thumbnails + "Upload" dropzone (jpg/png ≤ 5 MB; reject others with a clear message).
- `BoundingBoxCanvas.tsx`: draws the image and overlays boxes. Box coords from the API are `[ymin, xmin, ymax, xmax]` normalised **0–1000** → convert: `x = xmin/1000 * width`, etc. Colour by severity (`ok`/`warn`/`crit`); label chip with defect + confidence. Light scanline animation while scanning.
- **Run Vision Scan** button → spinner → result panel:
  - `visual_quality_score` gauge (1–10)
  - `defects_detected` as chips
  - `estimated_unit_count`
  - Shelf-life override block: "Printed label: 72 h" → "Recalibrated RSL: 19 h" with a red down-arrow and the `α_vision` used. Small "Source: USDA FoodKeeper — …" citation.
  - Badge `cached result` vs `live Gemini` so the demo is honest.

### Zone C — `EslMatrix.tsx` + `EslCard.tsx`
8 cards in a 4 × 2 grid, styled like e-ink shelf labels (light text on dark, monospace price).
Each card:
- Header: SKU id, name, Nutri-Score letter badge (A–E colours), packaging icon, ethylene badge (`producer` / `sensitive`).
- Inventory vs 24 h forecast bar: filled = on_hand, marker = forecast_24h, red overflow segment = surplus_risk_units.
- RSL countdown `19.0 h` (amber < 24 h, red < 8 h, pulsing at < 8 h).
- Price: struck-through base price → current price, markdown badge `−26%`. Flash the price briefly when it changes.
- State ribbon: `SURPLUS RISK`, `FLOOR`, `BUNDLED`, `SOLD OUT`.
- Click → `FormulaDrawer.tsx` (slide-in from right, over Zone E) showing the §5 calculation step by step with real numbers, including `ε = −2.0 (assumed)` and data sources.

### Zone D — `ExecutionModules.tsx`
- Tab 1 **Procurement**: table with the 7 columns from SIMULATION_ENGINE §7.4. Highlight rows changed by a weather event (lime flash) and show a "cut by rainstorm" tag.
- Tab 2 **Flash Surplus Bundles**: cards per box — contents, `$X.XX (−65%)`, countdown to expiry, status. Empty state: "No bundles yet — boxes appear when an item drops below 8 h shelf life and price cuts alone can't clear it."
- Below tabs (or a third tab if space is tight): Recharts `LineChart` of cumulative waste kg, Store A (baseline grey) vs Store B (accent), x-axis = sim day/hour.

### Zone E — `AgentLog.tsx`
- Terminal-style list, newest at bottom, auto-scroll unless the user has scrolled up ("Jump to latest" pill).
- Each line: `[D2 14:00] [PRICING_AGENT] message`. Expandable to show `data` JSON (citations, numbers).
- Filter chips per agent. Keep max 500 lines in memory.

### `ArchitectureModal.tsx`
A static SVG/HTML diagram of: Data sources (USDA, OFF, NOAA, Kaggle, FAOSTAT) → RAG / Seed data → Agents (5) → Orchestrator → ESL/PO/Bundles → UI. Each node shows live status from `/api/meta/architecture` (green dot = live, grey = fallback/snapshot). Animate an edge pulse when that agent logs.

## 5. Preset frames
Put three images in `src/assets/frames/` (`frame1.jpg`, `frame2.jpg`, `frame3.jpg`). Use photos with a licence that allows reuse (e.g. Unsplash/Pexels licence) or your own photos; record the source and licence in `src/assets/frames/CREDITS.md`. The backend has matching fixture JSON for each frame.

## 6. Quality bar
- `npm run typecheck`, `lint`, `build` all clean.
- No layout shift when numbers update (tabular nums, fixed widths).
- Respect `prefers-reduced-motion`: disable pulses and scanlines.
- Every interactive element is keyboard-reachable with a visible focus ring; buttons have `aria-label`s.
- Colour is never the only signal: severity also has an icon or text label.
