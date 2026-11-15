# Simulation Engine Specification — ShelfSense

This is the source of truth for everything in `backend/app/sim/`. Implement it exactly; if you must deviate, log it in `ARCHITECTURE.md → Decisions log`.

---

## 0. Corrections to the original blueprint

| # | Blueprint | Problem | What we do instead |
|---|---|---|---|
| 1 | `RSL = max(0, (SL − t) / (α·β))` | At constant α, RSL hits 0 at exactly `t = SL` whatever α is — a damaged batch spoils at the same time as a healthy one. α only shrinks the *displayed* number. | **Effective-age model** (§3): age accumulates at rate α·β per hour. Matches the blueprint formula at t=0 but spoils α·β times sooner. |
| 2 | `V_target = I / RSL`, `ΔQ% = …/V_forecast` | Divide-by-zero at RSL→0, overnight hours, empty stock. | Guards in §7. |
| 3 | Linear `ΔP% = ΔQ%/ε` | Big gaps produce >100% discounts. | Clamp to `P_floor`; anything still short goes to bundling. |
| 4 | Elasticity "from Kaggle" | Favorita has a promo flag but no clean elasticity. | ε is a **configured assumption** per category within the blueprint's −1.4 … −2.2 range, labelled "assumed" in the UI. |
| 5 | "Net Margin Recovered" | Not precisely defined. | `GM_B − GM_A`, where GM = revenue − cost of all goods received (§8). |
| 6 | FAOSTAT retail loss baseline | FAO's headline Food Loss Index stops *before* retail. | Use retail-stage records from FAO's Food Loss & Waste database (or UNEP Food Waste Index) — see DATA_SOURCES. |
| 7 | Vision changes RSL "in Store B" | If decay only exists in B, the comparison is rigged. | Decay is **physical and shared** by both stores; vision only gives Store B **knowledge** of it (§3.3). |

---

## 1. Time

- `tick` = integer simulated hours since Day 1 00:00. A cycle is ticks `0 … 167`.
- `day = tick // 24 + 1`, `hour = tick % 24`, `dow = (start_dow + tick // 24) % 7` (default `start_dow = 0` = Monday).
- Store open hours: **07:00–21:59** (demand only when open).
- Deliveries arrive at **06:00**. Store B's PO for tomorrow is computed at **21:00**.

## 2. Configuration (`data/seed/skus.json`)

```jsonc
{
  "sku_id": "STRW-01",
  "name": "Organic Strawberries 1 lb",
  "category": "berries",              // keys into hour_share + exposure tables
  "unit_weight_kg": 0.454,
  "base_price_usd": 4.99,
  "unit_cost_usd": 2.80,
  "sl_nominal_hours": 96,             // from FoodKeeper (Phase 2)
  "elasticity": -2.0,                 // assumed, see §0.4
  "price_floor_ratio": 0.40,          // P_floor = ratio × P_base
  "base_daily_units": 60,             // from Favorita profile (Phase 2)
  "weather_exposure": 1.0,            // 0..1, how much ambient stress reaches this SKU
  "bundle_group": "smoothie",
  "supplier": "Valley Berry Co.",
  "off": { "barcode": "…", "nutri_score": "a", "packaging": "plastic clamshell", "ethylene": "sensitive" }
}
```

Illustrative starting values (Phase 1 uses these; Phase 2 replaces SL and daily units with derived data):

| SKU | Unit kg | Price | Cost | SL h | ε | Daily units | Exposure | Group |
|---|---|---|---|---|---|---|---|---|
| Organic Strawberries | 0.454 | 4.99 | 2.80 | 96 | −2.0 | 60 | 1.0 | smoothie |
| Cavendish Bananas (bunch) | 1.00 | 1.99 | 1.00 | 120 | −1.6 | 90 | 1.0 | smoothie |
| Atlantic Salmon Fillet | 0.45 | 12.99 | 8.00 | 48 | −1.8 | 25 | 0.2 | dinner |
| Whole Milk 1 gal | 3.90 | 4.29 | 2.90 | 144 | −1.4 | 80 | 0.2 | — |
| Artisanal Sourdough | 0.68 | 5.49 | 2.20 | 48 | −2.2 | 40 | 0.6 | toast |
| Hass Avocado | 0.20 | 1.49 | 0.70 | 96 | −1.9 | 70 | 1.0 | toast |
| Baby Spinach 5 oz | 0.142 | 3.99 | 2.00 | 96 | −1.7 | 45 | 0.8 | dinner |
| Cherry Tomatoes 1 pt | 0.30 | 3.49 | 1.60 | 120 | −1.6 | 40 | 1.0 | toast |

Global config (`SimConfig`): `seed`, `start_dow`, `traffic_rain_mult = 0.78`, `rain_duration_h = 12`, `humidity_spike_mult = 1.78`, `cold_chain_sl_mult = 0.70`, `bundle_rsl_threshold_h = 8`, `bundle_discount = 0.65`, `bundle_base_rate_per_h = 1.5`, `store_a_par_mult = 1.25`, `store_a_markdown = 0.50`, `safety_z = 1.0`, `max_demand_mult = 3.0`, `price_hysteresis = 0.02`, `auto_scan_every_h = 6`.

## 3. Shelf life

### 3.1 Batch
```python
@dataclass
class Batch:
    batch_id: str
    sku_id: str
    qty: int
    received_tick: int
    # physical truth (identical in Store A and B for the same delivery)
    sl_true: float            # hours; nominal × cold-chain multiplier if abused
    alpha_true: float = 1.0   # visual degradation multiplier, 1.0..3.0
    age_true: float = 0.0     # effective age, hours
    # Store B's belief (Store A never updates beliefs)
    sl_known: float           # starts at sl_nominal
    alpha_known: float = 1.0
    age_known: float = 0.0
    inspected: bool = False
```

### 3.2 Per-tick update
```
β_sku   = 1 + (β_env − 1) × weather_exposure
age_true  += alpha_true  × β_sku × 1h
age_known += alpha_known × β_sku × 1h

RSL_true  = max(0, (sl_true  − age_true)  / (alpha_true  × β_sku))
RSL_known = max(0, (sl_known − age_known) / (alpha_known × β_sku))
printed_remaining = sl_nominal − (tick − received_tick)      # what the label says
```
A batch is **removed as waste** when `age_true ≥ sl_true` (actually spoiled) **or** `printed_remaining ≤ 0` (past date — must be pulled). This applies to both stores.

### 3.3 Knowledge (Store B only)
Store B updates its belief when a batch is **inspected**: `sl_known ← sl_true`, `alpha_known ← alpha_true`, `age_known ← age_true`, `inspected ← True`. Inspection happens on:
1. A manual vision scan (Zone B) targeting that SKU.
2. Receipt of a delivery flagged by a cold-chain event ("immediate vision re-evaluation").
3. An automatic camera sweep every `auto_scan_every_h` hours for camera-covered SKUs (`STRW-01`, `BANA-01` in Bay 2).

A **preset frame scan is treated as ground truth for that bay**: it sets `alpha_true` on the SKU's oldest batch in **both** stores (the shelves are identical), then marks Store B's copy inspected. This keeps the comparison fair.

### 3.4 Environment
```
β_env = 1 + 0.5 × clamp((RH − 50) / 50, 0, 1)        # RH = relative humidity %, range 1.0..1.5
```
Baseline RH comes from the NOAA snapshot. A rainstorm sets `RH = min(98, RH_base × humidity_spike_mult)` for `rain_duration_h`, then decays linearly back over 6 h.

## 4. Demand

### 4.1 Expected demand (the forecast)
```
λ(sku, tick) = base_daily_units × dow_weight[dow] × hour_share[category][hour] × traffic(tick)
```
- `hour_share[category]` sums to 1.0 over open hours; 0 when closed.
- `dow_weight` averages 1.0 over the week.
- `traffic(tick) = traffic_rain_mult` during a storm, else 1.0 (or the NOAA-derived modifier, §7.3).

`V_forecast` for pricing is the **average over the risk horizon** `H = ceil(RSL_known)` hours:
```
V_forecast = Σ_{h=tick}^{tick+H−1} λ(sku, h) / H
```
(Averaging over wall-clock hours, closed hours included, matches `V_target`, which also uses wall-clock RSL.)

### 4.2 Price response
```
price_mult(P) = clamp(1 + ε × (P / P_base − 1), 0, max_demand_mult)
```
Store A at a 50% markdown with ε = −1.8 → multiplier 1.9.

### 4.3 Realised demand — common random numbers
For each `(sku, tick)` draw one uniform `u` from `rng.uniform(seed, "demand", sku_idx, tick)`. Then
```
demand_A = poisson_inv_cdf(u, λ × price_mult(P_A))
demand_B = poisson_inv_cdf(u, λ × price_mult(P_B))
```
Same `u` for both stores ⇒ any difference comes from policy, not luck. Implement `poisson_inv_cdf` in NumPy (λ < 200; no SciPy needed).

### 4.4 Sales
`sold = min(demand, on_hand)`, allocated **FEFO** (oldest `received_tick` first). Revenue += `sold × P`. Units in bundles are not on the shelf.

## 5. Pricing (Store B)

Per SKU, each tick, using batches sorted FEFO with `RSL_known` values:

### 5.1 Velocity gap (FEFO-aware)
```
V_target = max over batches b of ( Σ_{j ≤ b} qty_j ) / RSL_known_b       # skip b with RSL_known_b == 0
```
(The most constrained batch decides; for one batch this is exactly `I / RSL`.)

If `V_target ≤ V_forecast` → no risk, `ΔQ% = 0`.
Else **Surplus Risk State**:
```
ΔQ% = (V_target − V_forecast) / V_forecast × 100
ΔP% = ΔQ% / ε                                    # negative
P_raw = P_base × (1 + ΔP% / 100)
P_new = max(P_floor, P_raw),  P_floor = price_floor_ratio × P_base
```
- Round `P_new` to cents.
- **Hysteresis:** only publish a new ESL price if `|P_new − P_current| / P_base ≥ price_hysteresis`.
- Prices may go back up when risk falls (e.g. after a sale-out of the oldest batch).
- `floor_bound = (P_raw < P_floor)` → candidate for bundling (§6).

### 5.2 Display helpers (ESL card)
- `forecast_24h = Σ_{h=tick}^{tick+23} λ(sku, h) × price_mult(P_current)`
- `surplus_risk_units = max(0, on_hand − Σ_{h<min(24, RSL_known_oldest)} λ × price_mult)`
- `markdown_pct = 1 − P_current / P_base`

### 5.3 Store A pricing
`P_A = P_base`, except when the oldest batch has `printed_remaining ≤ 24` → `P_A = P_base × (1 − store_a_markdown)`.

## 6. Flash Surplus Bundling (Store B)

**Trigger** (checked each tick): a batch with `qty > 0`, `RSL_known < bundle_rsl_threshold_h`, and either `floor_bound` is true or `qty > Σ_{h<RSL_known} λ × price_mult(P_floor)`.

**Composition:** pull the excess units (`qty − expected floor-price sales`) of all triggered SKUs into a pool. Build boxes greedily: each **Flash Surplus Mystery Box** takes up to 3 units, preferring different SKUs within the same `bundle_group` (e.g. toast = sourdough + avocado + cherry tomatoes), then any SKU. A box needs ≥ 2 units.

**Price:** `box_price = (1 − bundle_discount) × Σ base prices of contents` (i.e. 65% off).

**Sales:** while open, boxes sell with `Poisson(bundle_base_rate_per_h × traffic)` per hour (rng stream `"bundles"`), FIFO by box creation. A box expires — and its contents count as waste — when any component's `RSL_true` hits 0.

Bundled units leave the shelf immediately; they count as **diverted** when sold.

## 7. Procurement

### 7.1 Store A — static order-up-to
At 06:00: `order_A = max(0, par_A − on_hand_A)`, `par_A = ceil(store_a_par_mult × base_daily_units)`. No weather, no forecast.

### 7.2 Store B — demand-aligned throttling (computed at 21:00, delivered 06:00)
```
D̂_{t+1}      = Σ_{h ∈ tomorrow} λ(sku, h)                     # with tomorrow's traffic modifier
I_carryover = Σ_b qty_b where RSL_known_b ≥ 15                 # still sellable through tomorrow ~noon
              − Σ_{h ∈ rest of today, open} λ(sku, h)          # expected sales before close
S_buffer    = safety_z × sqrt(D̂_{t+1})                        # Poisson std dev
O_{t+1}     = max(0, ceil(D̂_{t+1} − I_carryover + S_buffer))
```

### 7.3 Weather modifier
`traffic_tomorrow = 1 − 0.22 × p_heavy_rain`, where `p_heavy_rain` is from the NOAA forecast (0..1), or `traffic_rain_mult` if a storm event is active/scheduled for tomorrow.

### 7.4 PO table columns (Zone D tab 1)
`SKU`, `Supplier`, `Standard Baseline Order` (= `order_A` for the same SKU), `Projected Carryover`, `Weather Demand Modifier`, `AI Adjusted PO Quantity` (= `O_{t+1}`), `Waste Prevention Delta` (= baseline − AI, in units and kg).

### 7.5 Initial state
Tick 0: both stores hold `par_A` fresh units of every SKU (`age = 0`, received at tick 0). Identical start.

## 8. Events

| Event | Effect |
|---|---|
| `rainstorm` | Traffic × 0.78 and RH spike for `rain_duration_h` from the next tick. Store B's PO for tomorrow is recomputed immediately (`PROCUREMENT_AGENT` logs the cut). |
| `cold_chain_delay` (payload: list of SKUs, default strawberries/spinach/salmon) | The **next** delivery of those SKUs arrives with `sl_true = 0.70 × sl_nominal` in **both** stores. Store B inspects on receipt. Option `immediate=true` injects an emergency delivery now (for demos). |
| `vision_override` (payload: sku_id, alpha, frame_id, detections) | Sets `alpha_true` on that SKU's oldest batch in both stores; Store B marks it inspected. |

All events go into `state.event_log` with their tick.

## 9. KPIs

```
W_X        = Σ wasted units × unit_weight_kg                 (per store, kg)
waste_reduction_pct = (W_A − W_B) / W_A × 100                (show "—" if W_A == 0)
food_diverted_kg    = W_A − W_B                              (waste avoided vs baseline)
co2e_avoided_kg     = food_diverted_kg × co2e_factor[category]   (FAO-derived, per category)
GM_X       = revenue_X − Σ (units received × unit_cost)
net_margin_recovered_usd = GM_B − GM_A
```
Also track per store: units sold, revenue, units wasted, $ written off (`wasted × unit_cost`), plus an hourly series for charts.

## 10. Tick order (fixed — determinism depends on it)

1. Apply queued events (log each).
2. Update environment: RH, `β_env`, traffic.
3. If `hour == 6`: deliveries (Store A order, Store B PO). Inspect cold-chain-flagged batches in B.
4. Auto camera sweep if `tick % auto_scan_every_h == 0`.
5. **Demand agent:** compute λ for this hour and horizons.
6. **Pricing agent:** Store B prices (§5); Store A prices (§5.3).
7. **Bundling agent:** create boxes (§6).
8. Realised demand + FEFO sales for both stores; box sales.
9. Age all batches (§3.2); remove spoiled/expired → waste; expire boxes.
10. If `hour == 21`: **Procurement agent** computes tomorrow's PO.
11. Compute KPIs and append the chart point.

## 11. Edge cases (must not crash)
- `RSL_known == 0` → skip that batch in `V_target`; it will be removed at step 9.
- `V_forecast == 0` (e.g. overnight horizon shorter than time to opening) → set `P_new = P_floor`, mark `floor_bound`.
- `on_hand == 0` → no pricing change; show "SOLD OUT".
- `W_A == 0` → KPI shows "—", not NaN/∞.
- ε must be < 0; validate config on load.
- Sim past tick 167 → controller stops; `play` is a no-op until reset.

## 12. Test vectors (put these in `tests/test_sim_*.py`)

| Case | Input | Expected |
|---|---|---|
| RSL healthy | sl=72, α=1, β=1, 10 ticks | age=10, RSL=62 |
| RSL damaged | sl=72, α=2 from tick 0, β=1, 10 ticks | age=20, RSL=26; spoils at tick 36 (blueprint formula would wrongly give spoil at 72) |
| RSL humid | sl=96, α=1, β_env=1.3, exposure=1.0, 10 ticks | age=13, RSL=(96−13)/1.3 ≈ 63.85 |
| Pricing | I=40, RSL=10, V_fc=2.5, ε=−2.0, P=4.99, floor 0.4 | V_t=4.0, ΔQ=60%, ΔP=−30%, P=3.49 |
| Floor clamp | same but V_fc=0.5 | ΔQ=700%, P_raw<0 → P=2.00 (floor), floor_bound=True |
| FEFO V_target | batches (10 @ RSL 5), (30 @ RSL 40) | max(10/5, 40/40)=2.0 |
| PO | D̂=60, carryover=18, z=1 | 60−18+7.746=49.75 → 50 |
| Price mult | ε=−1.8, P/P_base=0.5 | 1.9 |
| CRN | same u, λ_B > λ_A | demand_B ≥ demand_A |
| Determinism | two runs, seed 42, same events | identical KPI series |

## 13. Acceptance for the engine (Phase 1 exit)
- `cli --hours 168` runs in < 2 s.
- Across seeds 1–20 with **no events**, report mean ± std of waste reduction. Also run the scripted demo timeline (rain Day 2 10:00, cold-chain Day 3, thermal-anomaly scan Day 4). Record both in `docs/IMPLEMENTATION_PLAN.md`.
- If the no-event mean is < 30%, **do not** tweak per-seed. Adjust global, defensible parameters (Store A par, safety z) and log the change and reason in the Decisions log.
