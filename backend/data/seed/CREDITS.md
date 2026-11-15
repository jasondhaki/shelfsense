# Seed data credits

Every number the simulation uses that did not come from a public source is labelled
**assumed** here and in `scripts/sku_base.json`.

| Source | Used for | Licence | Retrieved | Status |
|---|---|---|---|---|
| **USDA FSIS FoodKeeper** — https://catalog.data.gov/dataset/fsis-foodkeeper-data | `sl_nominal_hours` (lower bound of the storage range), RAG corpus | CC0 (US Government work) | — | **Pending**: FSIS blocks automated downloads; download `foodkeeper.json` manually into `data/raw/foodkeeper/`. Until then `sl_nominal_hours` is illustrative (see `sl_source` in `skus.json`). |
| **Open Food Facts** — https://world.openfoodfacts.org (API v2) | `off.product_name`, `off.nutri_score`, `off.packaging` for 6 reference barcodes | ODbL 1.0 (database), DbCL (contents). Attribution: "Data from Open Food Facts". | 2026-11-15 | Done. Avocado and cherry tomatoes have no usable OFF entry → `null`. Empty OFF packaging falls back to a hand-entered description. |
| **Kaggle — Corporación Favorita Grocery Sales Forecasting** — https://www.kaggle.com/competitions/favorita-grocery-sales-forecasting/data | `dow_weight` per category (family aggregates only), promo lift sanity check | Competition data — only derived aggregates are committed, never raw rows | — | **Pending**: download `train.csv` + `items.csv` into `data/raw/favorita/`. Until then `dow_weight` is flat (1.0). |
| **NOAA National Weather Service API** — https://api.weather.gov | `weather_snapshot.json` (New York, NY): baseline RH, per-day heavy-rain probability | US Government work, public domain | 2026-11-15 18:44 UTC | Done. |
| **FAO (2011)**, Gustavsson et al., *Global Food Losses and Food Waste — Extent, Causes and Prevention*, Annex 4 (North America & Oceania, "Distribution: Supermarket Retail") — https://www.fao.org/4/mb060e/mb060e.pdf | `retail_waste_pct` per category (Store A calibration target) | © FAO; figures cited | 2026-11-15 | Done. FAO labels these figures "estimated/assumed". |
| **Poore & Nemecek (2018)**, *Science* 360:987, via Our World in Data — https://ourworldindata.org/grapher/ghg-per-kg-poore | `co2e_kg_per_kg` per category | CC BY 4.0 (OWID) | 2026-11-15 | Done. Avocado → "Other Fruit", spinach → "Other Vegetables", bread → "Wheat & Rye" are proxies. |
| **USDA AMS NOP, Ethylene — Handling Technical Report (2023)** — https://www.ams.usda.gov/sites/default/files/media/2023Technical_Report_Ethylene_Handling.pdf | ethylene `producer` (banana, avocado, tomato) / non-climacteric (strawberry) | US Government work | 2026-11-15 | Done. |
| **Suslow & Cantwell, UC Davis Postharvest Center — Spinach** — https://postharvest.ucdavis.edu/node/8161 | ethylene `sensitive` (spinach) | © UC Regents; cited | 2026-11-15 | Done. |

## Assumptions (not from a dataset)
- Price elasticity ε per SKU (within the blueprint's −1.4 … −2.2 range).
- Prices, unit costs, suppliers (fictional), `base_daily_units`, `weather_exposure`.
- `hour_share` within-day traffic curve (Favorita is daily data).
- `delivery_every_days` supplier schedule (bakery and seafood daily, everything else every other day), identical for both stores.
- `demand_daily_cv = 0.3`: day-level forecast error per SKU (Gamma, mean 1), shared by both stores, unseen by forecasts.
- `fresh_picker_share = 0.5` (half of shoppers take the newest unit) and `store_a_par_mult = 2.0` — chosen in Phase 2 so Store A's waste by category lands near the FAO retail figures; see `docs/ARCHITECTURE.md` decisions log.
