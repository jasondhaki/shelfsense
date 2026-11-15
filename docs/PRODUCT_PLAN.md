# FoodSphere AI: Product & System Blueprint

**System Domain:** Autonomous Inventory, Vision Monitoring & Dynamic Pricing Engine  
**Core Objective:** Reduce simulated retail food waste by at least $30\%$ through demand-aligned ordering, multimodal shelf inspection, and autonomous dynamic discounting.

---

## 1. System Overview & Core Simulation Paradigm

### System Vision: Autonomous Retail Operations Center & Time-Lapse Simulator
Rather than functioning as a passive reporting dashboard that relies on manual human intervention, FoodSphere AI operates as an **interactive simulation engine and autonomous command center**. The system continuously ingests environmental, visual, and historical retail data to recalculate true product shelf life, dynamically adjust SKU pricing via price elasticity models, and throttle upstream supplier purchase orders in real time.

### Parallel Twin-Store Simulation Engine
To quantify waste reduction and financial impact, the core state engine runs two parallel retail store models under identical consumer traffic and environmental conditions:
1. **Store A (Baseline / Traditional FIFO Retail):** Operates on static reorder points, relies strictly on printed manufacturer expiration dates, and applies flat manual markdowns ($50\%$) only on the final day before expiration.
2. **Store B (FoodSphere AI Engine):** Operates on NOAA weather-adjusted demand forecasting, vision-recalibrated remaining shelf life ($RSL$), continuous price elasticity discounting, Automated Surplus Bundling, and dynamic supplier order throttling.

---

## 2. User Interface Architecture: The 5-Zone Layout

The application interface is structured as a single-screen, dark-mode operational command center divided into five functional zones:

### Zone A: Top Telemetry & Simulation Controller Bar
The global state controller and top-level KPI telemetry bar spanning the header of the application.

* **Simulation Playback Controls:**
  * `Play (1x)`: Advances simulated time at $1\text{ simulated hour per second}$.
  * `Fast-Forward`: Accelerates simulation across a full $7\text{-day}$ ($168\text{-hour}$) retail cycle.
  * `Pause` & `Reset Cycle`: Freezes current state inspection or resets inventory to Day $1$ baseline.
* **Environmental & Supply Chain Event Triggers (Chaos Injectors):**
  * **Trigger Heavy Rainstorm (NOAA Event):** Simulates an immediate drop in store foot traffic ($-22\%$) and spikes ambient humidity ($+78\%$), forcing agents to recalculate clearance velocities and cut next-day purchase orders.
  * **Trigger Cold-Chain Transit Delay:** Simulates an incoming delivery where thermal abuse reduces baseline shelf life by $30\%$ upon arrival, triggering immediate vision re-evaluation and rapid markdown protocols.
* **North-Star Telemetry Cards:**
  1. **Simulated Waste Reduction ($\%$):** Real-time differential between Store A and Store B cumulative food waste (Target threshold: $\ge 30\%$).
  2. **Total Food Diverted from Landfill ($\text{kg}$):** Cumulative weight of perishable inventory sold prior to spoilage, benchmarked against **FAOSTAT** retail loss baselines.
  3. **Net Margin Recovered ($\$$):** Financial delta comparing revenue retained via dynamic discounting against $100\%$ write-off losses in the baseline store.
  4. **System Architecture View Trigger:** Modal toggle (`[System Architecture]`) displaying the real-time multi-agent orchestration and data ingestion topology.

### Zone B: Virtual CCTV Smart-Cam Inspector (Left Panel)
A deterministic multimodal computer vision inspection module simulating an aisle optical sensor (`CAM-04: FRESH PRODUCE AISLE — BAY 2`).

* **Preset Optical Frame Carousel & Custom Ingestion:**
  * `Frame 1: Day 1 Morning (Optimal State)` — Fresh organic strawberries and green-tip Cavendish bananas at peak visual quality.
  * `Frame 2: Day 3 Afternoon (Early Degradation)` — Bananas exhibiting sugar spotting; strawberries showing minor condensation and surface bruising.
  * `Frame 3: Thermal Anomaly State (Accelerated Decay)` — Premature ripening and cellular breakdown occurring $48\text{ hours}$ ahead of the printed barcode expiration date.
  * `Frame 4: Custom Image Ingestion Dropzone` — File upload/drag-and-drop input allowing arbitrary produce images to be analyzed by the Multimodal Vision LLM pipeline.
* **Vision Telemetry & Bounding Box Overlay:**
  When `Run Vision Scan` is executed on an active frame:
  1. **2D Bounding Box Rendering:** Renders normalized coordinate overlays (`[ymin, xmin, ymax, xmax]`) onto the canvas color-coded by severity (Green = Optimal, Amber = Accelerated Ripening, Red = Immediate Clearance Required).
  2. **Structured Multimodal Extraction:** Displays the parsed JSON telemetry from the Vision model:
     * `visual_quality_score`: Float ($1.0\text{--}10.0$)
     * `defects_detected`: Array of visual markers (e.g., `["stem_browning", "surface_moisture", "ethylene_bruising"]`)
     * `estimated_unit_count`: Integer count of visible packages/units on the shelf.
  3. **Shelf-Life Override Calculation:** Displays the delta between the static printed expiration date and the AI-recalibrated Remaining Shelf Life ($RSL$) after cross-referencing **USDA FoodKeeper** storage degradation rules:
     * *Printed Label Remaining Life:* $72\text{ hours}$
     * *Recalibrated $RSL$:* $19\text{ hours}$ (Dispatches state update to Pricing Agent).

### Zone C: Electronic Shelf Label (ESL) Matrix (Center Panel)
A real-time grid of digital price tags representing high-perishability SKUs (*Organic Strawberries, Cavendish Bananas, Atlantic Salmon Fillets, Whole Milk, Artisanal Sourdough, Hass Avocados, Baby Spinach*).

Each digital SKU card contains:
* **Product Metadata Header:** SKU ID, product name, Nutri-Score, packaging classification, and ethylene gas sensitivity badge sourced from **Open Food Facts**.
* **Inventory vs. Demand Velocity Bar:** Visual progress bar comparing `Current Shelf Stock` against `24h Forecasted Sales Velocity`, highlighting exact `Surplus Risk Units`.
* **Live Spoilage Countdown ($RSL$):** Dynamic countdown timer tracking hours remaining before product quality drops below saleable thresholds.
* **Dynamic Price & Markdown Display:** Displays base retail price, current active dynamic price, and percentage markdown badge (e.g., `$4.99` $\rightarrow$ `$3.69 (-26%)`).
* **Microeconomic Formula Inspector:** Clicking any ESL card expands a detail drawer displaying the real-time variables ($RSL$, Target Velocity, Forecast Velocity, and Price Elasticity $\epsilon$) driving that SKU's current price.

### Zone D: Upstream & Downstream Execution Modules (Bottom Center Panel)
A two-tab operational panel managing supplier intake and last-mile clearance.

* **Tab 1: Upstream Demand-Aligned Ordering (Procurement Module):**
  * Displays automated next-day Purchase Orders (PO) queued for external suppliers.
  * Calculates adjustments by combining current shelf carryover, **Kaggle** historical day-of-week sales velocity, and **NOAA** $72\text{-hour}$ weather modifiers.
  * Columns: `SKU`, `Supplier`, `Standard Baseline Order`, `Projected Carryover`, `Weather Demand Modifier`, `AI Adjusted PO Quantity`, and `Waste Prevention Delta`.
* **Tab 2: Downstream Flash Surplus Bundling (Last-Mile Clearance Module):**
  * Automatically triggers when a SKU's recalibrated $RSL$ drops below a critical threshold ($RSL < 8\text{ hours}$) and single-item price elasticity is insufficient to clear remaining stock.
  * Groups complementary short-dated SKUs (e.g., *Artisanal Sourdough + Hass Avocados + Cherry Tomatoes*) into a single **"Flash Surplus Mystery Box"** priced at a flat $65\%$ clearance discount for local consumer pickup.

### Zone E: Multi-Agent Reasoning & RAG Telemetry Log (Right Sidebar)
A streaming event terminal displaying inter-agent communication, RAG vector retrievals, and state mutations with timestamps:
* `[VISION_AGENT]`: Logs optical scan outputs, defect classifications, and visual decay coefficients ($\alpha_{\text{vision}}$).
* `[RAG_KNOWLEDGE_AGENT]`: Logs specific document retrievals from **USDA FoodKeeper** and **Open Food Facts** (e.g., ethylene cross-contamination rules, humidity multipliers).
* `[DEMAND_AGENT]`: Logs time-series velocity predictions combining **Kaggle** baselines with **NOAA** weather anomalies.
* `[PRICING_AGENT]`: Logs Price Elasticity of Demand ($PED$) calculations and ESL price updates.
* `[PROCUREMENT_AGENT]`: Logs automated modifications to upcoming supplier Purchase Orders.

---

## 3. Core Mathematical & Economic Engine

The simulation state and autonomous agent decisions are governed by four sequential mathematical models:

### 3.1 Vision-Adjusted Remaining Shelf Life ($RSL$)
Rather than decrementing shelf life linearly from a printed date, $RSL$ (in hours) is dynamically computed at each tick using the **USDA FoodKeeper** baseline shelf life ($SL_{\text{USDA}}$), elapsed time ($t$), the Vision LLM degradation penalty ($\alpha_{\text{vision}} \in [1.0, 3.0]$), and the **NOAA** ambient environmental stress factor ($\beta_{\text{weather}} \in [1.0, 1.5]$):

$$RSL = \max\left(0, \frac{SL_{\text{USDA}} - t}{\alpha_{\text{vision}} \cdot \beta_{\text{weather}}}\right)$$

### 3.2 Velocity Gap Detection
For each SKU, the engine compares the **Target Clearance Velocity** ($V_{\text{target}}$, in units/hour) required to clear current inventory ($I_{\text{current}}$) before $RSL$ reaches zero against the **Forecasted Demand Velocity** ($V_{\text{forecast}}$):

$$V_{\text{target}} = \frac{I_{\text{current}}}{RSL}$$

When $V_{\text{target}} > V_{\text{forecast}}$, the SKU enters a **Surplus Risk State**. The required percentage increase in quantity demanded ($\Delta Q\%$) to achieve zero waste is:

$$\Delta Q\% = \left(\frac{V_{\text{target}} - V_{\text{forecast}}}{V_{\text{forecast}}}\right) \times 100$$

### 3.3 Optimal Price Elasticity Discounting ($PED$)
Using the SKU category's **Price Elasticity of Demand** ($\epsilon$, typically ranging from $-1.4$ to $-2.2$ for fresh perishables), the **Pricing Agent** calculates the minimum necessary price reduction ($\Delta P\%$) to accelerate sales velocity to match $V_{\text{target}}$ while maximizing retained margin:

$$\Delta P\% = \frac{\Delta Q\%}{\epsilon}$$

$$P_{\text{new}} = \max\left(P_{\text{floor}}, P_{\text{base}} \times \left(1 + \frac{\Delta P\%}{100}\right)\right)$$

Where $P_{\text{floor}}$ represents the minimum liquidation price threshold before triggering Downstream Flash Bundling.

### 3.4 Demand-Aligned Order Throttling
To prevent upstream over-supply, the **Procurement Agent** computes the next cycle's supplier order quantity ($O_{t+1}$) using weather-adjusted forecasted demand ($\hat{D}_{t+1}$), projected unspoiled carryover inventory ($I_{\text{carryover}}$), and a dynamic safety stock buffer ($S_{\text{buffer}}$):

$$O_{t+1} = \max\left(0, \hat{D}_{t+1} - I_{\text{carryover}} + S_{\text{buffer}}\right)$$

---

## 4. Data Sources & Integration Specification

| Data Source | System Integration & Processing Role | UI Surface & Telemetry Output |
| :--- | :--- | :--- |
| **USDA FoodKeeper Data** | Structured/vectorized into the RAG knowledge base. Supplies baseline shelf life ($SL_{\text{USDA}}$), optimal storage temperature ranges, and accelerated decay rules upon seal breakage or thermal abuse. | Cited in the **Multi-Agent Reasoning Log** and displayed in the **Vision Inspector** during $RSL$ recalibration. |
| **Open Food Facts** | Supplies SKU-level product metadata, Nutri-Score, ingredient perishability profiles, packaging types, and ethylene gas sensitivity classifications. | Rendered as metadata badges on **Electronic Shelf Label (ESL)** cards and passed as context to the RAG pipeline. |
| **NOAA Weather API** | Provides real-time and $72\text{-hour}$ forecasted temperature, precipitation, and relative humidity. Modifies consumer foot-traffic multipliers and ambient spoilage factor ($\beta_{\text{weather}}$). | Powers the **Header Weather Telemetry Widget** and the **Weather Anomaly Trigger** state calculations. |
| **Kaggle Grocery Sales Dataset** | Supplies historical baseline SKU sales velocity ($V_{\text{forecast}}$), day-of-week seasonality weights, and category-specific price elasticity ($\epsilon$) coefficients. | Drives the **Inventory vs. Forecasted Demand** bars on ESL cards and the $7\text{-day}$ simulation curves. |
| **FAOSTAT** | Provides baseline retail loss percentages by commodity group (fruits/vegetables, dairy, meat, bakery) and $\text{CO}_2\text{e}$ emission factors per $\text{kg}$ of food waste. | Calibration baseline for **Store A (Traditional Retail)** waste rates and the **Food Saved ($\text{kg}$)** KPI counter. |

---

## 5. End-to-End Functional Workflows & State Transitions

The application state machine supports three primary operational workflows:

### Workflow 1: Multimodal Vision Inspection $\rightarrow$ Shelf-Life Override $\rightarrow$ Dynamic Markdown
1. **Trigger:** User selects a camera frame in **Zone B** (or uploads an image) and triggers `Run Vision Scan`.
2. **Vision Analysis:** The image is processed to extract bounding boxes, defect classifications, and a `visual_quality_score`, calculating a new $\alpha_{\text{vision}}$ decay multiplier.
3. **RAG Retrieval:** The system queries **USDA FoodKeeper** and **Open Food Facts** records for the detected SKU to retrieve storage sensitivity rules and computes the updated $RSL$.
4. **Pricing Execution:** The updated $RSL$ increases $V_{\text{target}}$. The **Pricing Agent** computes $\Delta P\%$ via the price elasticity formula and updates the corresponding **ESL Card** in **Zone C** with the new discounted price and adjusted sales velocity.
5. **Logging:** Each step emits a structured log entry into **Zone E**.

### Workflow 2: Environmental Shock $\rightarrow$ Demand Recalibration $\rightarrow$ Order Throttling
1. **Trigger:** User activates an environmental event (e.g., `Heavy Rainstorm`) in **Zone A**.
2. **Forecast Update:** **NOAA** weather parameters update the global store state, reducing forecasted foot traffic ($V_{\text{forecast}}$ drops across all SKUs) and elevating humidity stress ($\beta_{\text{weather}}$).
3. **Dual Agent Action:**
   * **Pricing Agent** recalculates markdowns for immediate shelf stock at risk of missing clearance targets due to lower foot traffic.
   * **Procurement Agent** recalculates $\hat{D}_{t+1}$ and immediately reduces pending supplier Purchase Order quantities in **Zone D (Tab 1)**.

### Workflow 3: Time-Lapse Simulation & Critical Surplus Bundling
1. **Trigger:** User engages `Play` or `Fast-Forward` in **Zone A**.
2. **Tick Execution:** On each simulated hour tick:
   * Both **Store A** and **Store B** decrement inventory based on their active sales velocities ($V_{\text{baseline}}$ vs. $V_{\text{elasticity\_adjusted}}$).
   * Remaining Shelf Life ($RSL$) decrements for all active batches.
   * Any inventory where $RSL = 0$ is recorded as **Spoiled Waste** (incrementing waste counters in $\text{kg}$ and $\$$ lost).
   * Any SKU in **Store B** whose $RSL$ drops below $8\text{ hours}$ with remaining stock $> 0$ is automatically routed to **Zone D (Tab 2)** and packaged into a **Flash Surplus Mystery Bag** for rapid clearance.
3. **Telemetry Update:** Top-level KPI cards and comparison charts update in real time to reflect cumulative waste reduction ($\%$), weight saved ($\text{kg}$), and net margin recovered ($\$$).