# Data Sources & Seed Pipeline — ShelfSense

All five sources are free. The app **never depends on them at runtime** — offline scripts in `backend/scripts/` turn raw downloads into small JSON files in `backend/data/seed/`, which are committed. Only NOAA has an optional live call.

Raw downloads go in `backend/data/raw/` (git-ignored). Each script prints what it wrote and is safe to re-run.

> Verify every URL and field name when you implement — public datasets move. If something below turns out to be wrong, fix this doc and log it in the Decisions log.

## Gaps in the blueprint you should know about
1. **Ethylene sensitivity is not an Open Food Facts field.** Use a small hand-curated table (producer / sensitive / neutral) from postharvest references (e.g. university postharvest extension publications), stored in `data/seed/ethylene.json` and added to the RAG corpus with its citation.
2. **Fresh produce often has no Open Food Facts entry or Nutri-Score.** Pick packaged reference products (clamshell strawberries, bagged spinach, bottled milk, packaged sourdough) by barcode; if a field is missing, store `null` and the UI shows "n/a".
3. **Favorita is daily data, not hourly.** Day-of-week weights come from the data; the within-day curve (`hour_share`) is an assumption — a typical grocery traffic curve, labelled as such.
4. **NOAA's api.weather.gov only covers the US.** The simulated store is therefore placed in a US city (configurable). If you'd rather simulate a store in Dhaka, swap in Open-Meteo (free, no key) behind the same `WeatherNow` interface.
5. **FAOSTAT's Food Loss Index excludes retail.** For retail baselines, use retail-stage records from FAO's Food Loss and Waste database, or UNEP's Food Waste Index.

---

## 1. USDA FoodKeeper → `foodkeeper.json` + RAG corpus
- **What:** storage times (pantry / refrigerator / freezer) per food, with tips.
- **Get it:** the FoodKeeper dataset published by USDA FSIS (available as a downloadable data file on the US government open-data catalog). Download the JSON or spreadsheet version into `data/raw/foodkeeper/`.
- **Script:** `scripts/build_seed_foodkeeper.py`
  - Find the records for our 8 SKUs (strawberries, bananas, fresh fish/salmon, milk, bread, avocados, spinach/leafy greens, tomatoes).
  - Convert the refrigerator (or pantry, for bananas/bread/avocados/tomatoes) range to hours. Use the **lower bound** for `sl_nominal_hours` on a retail display, and keep the full range for reference.
  - Output `foodkeeper.json`: `{sku_id, foodkeeper_id, name, storage, min_days, max_days, metric, tips, sl_nominal_hours}`.
  - Also write one Markdown chunk per product to `data/rag/corpus/foodkeeper_<sku>.md` with the original wording of the tips and a `source:` header.
- **Used by:** `sl_nominal_hours` in `skus.json`, RSL citations, RAG.

## 2. Open Food Facts → fields merged into `skus.json`
- **API:** `GET https://world.openfoodfacts.org/api/v2/product/{barcode}.json?fields=product_name,nutriscore_grade,packaging,packaging_tags,categories_tags,image_front_small_url`
- Set a descriptive `User-Agent` (their API etiquette asks for one). Be gentle — 8 products, cache responses in `data/raw/off/`.
- **Script:** `scripts/build_seed_off.py` with a hard-coded `{sku_id: barcode}` map you choose.
- **Output fields:** `off.barcode, off.nutri_score, off.packaging, off.product_name`. Missing → `null`.
- **Licence:** ODbL (database) — keep attribution "Data from Open Food Facts" in the UI footer and in `CREDITS.md`.

## 3. Kaggle — Corporación Favorita Grocery Sales → `sales_profile.json`
- **What:** daily unit sales by store × item, with `items.csv` (`family`, `perishable`) and an `onpromotion` flag.
- **Get it:** download from Kaggle with your own account (Kaggle CLI or browser). `train.csv` is several GB — process it in chunks with pandas (`chunksize`) or with DuckDB; don't load it whole.
- **Script:** `scripts/build_seed_favorita.py` (run locally, not on Render)
  1. Join items, keep perishable families: PRODUCE, DAIRY, BREAD/BAKERY, SEAFOOD (map to our categories).
  2. For each family: `dow_weight[0..6]` = mean daily units by weekday ÷ overall mean.
  3. Daily volume per item (median of items in that family) → scale to `base_daily_units` for a mid-size store (document the scaling factor).
  4. Optional: promo lift by family = mean units on promo ÷ mean units off promo — report it next to the assumed ε as a sanity check; don't treat it as elasticity.
- **Output:** `{category: {dow_weight: [7 floats], base_daily_units: int, promo_lift: float|null}}`, plus a fixed `hour_share` curve per category (assumed, documented).
- **Licence:** competition data — commit **only these aggregates**, never raw rows. Note the source in `CREDITS.md`.

## 4. NOAA (api.weather.gov) → live `WeatherNow` + `weather_snapshot.json`
- **No API key**, but a `User-Agent` header with contact info is required.
- Flow: `GET /points/{lat},{lon}` → `properties.forecast` and `properties.forecastHourly` URLs → fetch hourly forecast.
- Extract for the next 72 h: `temperature`, `relativeHumidity.value`, `probabilityOfPrecipitation.value`, `shortForecast`.
- `p_heavy_rain` for tomorrow = max hourly precipitation probability tomorrow ÷ 100, but only counted if `shortForecast` mentions rain/showers/thunderstorms.
- **Script:** `scripts/snapshot_noaa.py` saves a real response to `weather_snapshot.json` (fallback + deterministic tests).
- Runtime: `services/noaa.py`, 30-min cache, 8 s timeout, falls back to the snapshot. The header badge shows which one is in use.
- **Determinism note:** live weather changes the simulation. Tests and the "demo" preset always use the snapshot. Live mode is a toggle.

## 5. FAO food loss & waste → `faostat.json`
- **What:** retail-stage loss/waste percentages by commodity group (fruits & vegetables, dairy, meat & fish, bakery/cereals).
- **Get it:** FAO's Food Loss and Waste database (filter: supply-chain stage = retail), and/or UNEP Food Waste Index report figures. Record exactly which rows/figures you used.
- **Output:** `{category: {retail_waste_pct: float, source: str, co2e_kg_per_kg: float, co2e_source: str}}`.
- **CO₂e factors:** per-kg emission factors by food group from a published source (FAO or peer-reviewed life-cycle studies). Keep `co2e_source` explicit.
- **Used for:**
  - **Calibration check:** Store A's simulated waste % per category should land in a plausible range of `retail_waste_pct`. If it's wildly off, adjust `store_a_par_mult` (globally) and log it.
  - `co2e_avoided_kg` KPI.

## 6. Final seed files (committed)
```
backend/data/seed/
├── skus.json               # merged: base config + FoodKeeper SL + OFF metadata + Favorita volumes
├── foodkeeper.json
├── ethylene.json
├── sales_profile.json
├── faostat.json
├── weather_snapshot.json
└── CREDITS.md              # every source, URL, licence, date downloaded
```
`scripts/build_seed_all.py` runs everything in order and validates the result against a Pydantic schema (fails loudly on missing fields).

## 7. Phase 1 shortcut
Phase 1 doesn't wait for any of this: it uses the illustrative table in SIMULATION_ENGINE §2 hard-coded in `skus.json`, a flat `dow_weight` of 1.0, an assumed `hour_share` curve, and a hand-written `weather_snapshot.json`. Phase 2 swaps in real data without changing engine code.
