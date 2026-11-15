# AI Pipeline — Vision & RAG — ShelfSense

Two AI components, both behind fallbacks so the demo runs with no key:
1. **Vision** — Gemini multimodal extracts structured shelf telemetry from an image.
2. **RAG** — retrieves FoodKeeper / Open Food Facts / ethylene / FAO snippets to justify agent decisions.

Use the official Google Gen AI Python SDK (`google-genai`). Model names come from `GEMINI_VISION_MODEL` and `GEMINI_EMBED_MODEL`; check Google AI Studio for which models are currently on the free tier and note them in `.env.example`. Respect free-tier rate limits: one vision call per user click, no automatic live calls in the tick loop.

---

## 1. Vision

### 1.1 Request
- Input: image bytes (preset frame or upload, resized client- or server-side to ≤ 1024 px longest edge, JPEG q≈85).
- Use **structured output** (JSON MIME type + response schema) so the reply is parseable without regex.
- Temperature 0.

**System / instruction prompt** (`app/agents/prompts/vision.txt`):
```
You are a retail shelf-inspection vision system for a grocery produce aisle.
Analyse the image and return ONLY JSON matching the schema.

For each distinct product group visible (e.g. a pile of bananas, a row of strawberry clamshells):
- label: one of ["strawberries","bananas","avocados","spinach","cherry_tomatoes","sourdough","salmon","milk","other"]
- box_2d: [ymin, xmin, ymax, xmax] normalised to 0-1000
- severity: "optimal" | "accelerated_ripening" | "clearance_required"
- defects: subset of ["stem_browning","surface_moisture","ethylene_bruising","sugar_spotting","mold","wilting","soft_spots","discoloration","leakage"]
- confidence: 0-1

Then give overall:
- visual_quality_score: 1.0 (inedible) to 10.0 (peak freshness), one decimal
- defects_detected: union of defects
- estimated_unit_count: integer count of visible packages/units
- primary_sku_label: the label covering the largest area
- rationale: one short sentence describing the visual evidence

Judge only what is visible. Do not guess expiry dates. If the image is not of food on a shelf, set primary_sku_label to "other" and visual_quality_score to null.
```

### 1.2 Response schema (Pydantic `VisionExtraction`)
```python
class Detection(BaseModel):
    label: SkuLabel
    box_2d: tuple[int, int, int, int]      # 0..1000, ymin,xmin,ymax,xmax
    severity: Literal["optimal","accelerated_ripening","clearance_required"]
    defects: list[Defect]
    confidence: float

class VisionExtraction(BaseModel):
    detections: list[Detection]
    visual_quality_score: float | None
    defects_detected: list[Defect]
    estimated_unit_count: int
    primary_sku_label: SkuLabel
    rationale: str
```
Validate the model reply with this schema. On validation failure: retry once; then fall back (preset → fixture; custom → 422 with a friendly message).

### 1.3 From extraction to α (deterministic, in `app/sim/shelf_life.py`)
```
α_quality = 1.0                          if q ≥ 8.0
          = 1.0 + (8.0 − q) × (2.0 / 7.0) if q < 8.0          # q=1 → 3.0
α_defects = +0.15 for each of {mold, leakage, ethylene_bruising} present
α_vision  = clamp(α_quality + α_defects, 1.0, 3.0)
```
Target SKU = `sku_hint` if provided, else map `primary_sku_label` → `sku_id`. `"other"` → no state change; the scan result still displays.

### 1.4 `VisionScanResult` (API response)
```jsonc
{
  "frame_id": "frame3",
  "mode": "cached" | "live",
  "extraction": VisionExtraction,
  "target_sku": "STRW-01",
  "alpha_vision": 2.29,
  "rsl_before_hours": 72.0,              // Store B belief before scan (oldest batch)
  "printed_remaining_hours": 72.0,
  "rsl_after_hours": 19.0,
  "foodkeeper_citation": { "title": "...", "chunk_id": "...", "text": "..." },
  "applied_at_tick": 81
}
```

### 1.5 Fixtures (`data/fixtures/vision/frame{1,2,3}.json`)
Generate them once in Phase 6 by running live mode on the three preset images, then **review and hand-correct** so the story reads well:
- Frame 1 → q ≈ 9.2, all `optimal`, no defects → α = 1.0.
- Frame 2 → q ≈ 6.4, bananas `sugar_spotting`, strawberries `surface_moisture` + minor bruising → α ≈ 1.6.
- Frame 3 → q ≈ 3.8, `clearance_required`, mold + ethylene bruising + soft spots → α ≈ 2.5.
Fixtures are what tests and cached mode use.

---

## 2. RAG knowledge agent

### 2.1 Corpus (`data/rag/corpus/*.md`)
One Markdown file per source record, each starting with a header:
```
---
source: USDA FoodKeeper
title: Strawberries — refrigerator storage
url: <dataset url>
sku_ids: [STRW-01]
---
<text>
```
Contents: FoodKeeper records for our SKUs (tips + storage times), Open Food Facts metadata summaries, ethylene compatibility table rows, humidity/temperature handling notes from extension publications, FAO retail-waste figures. Expect 50–200 chunks total. Chunk at ~500 characters on paragraph boundaries, keep the header metadata on every chunk.

### 2.2 Index (`scripts/build_rag_index.py`)
- **Vector:** embed each chunk with `GEMINI_EMBED_MODEL` → `data/rag/index.npz` (`embeddings` float32 matrix + `ids`) and `data/rag/chunks.json` (id → text + metadata). Normalise vectors.
- **BM25:** always also build `data/rag/bm25.json` (tokenised corpus) using `rank-bm25`, so retrieval works without a key.
- Commit both (they're small).

### 2.3 Retrieval (`app/rag/retriever.py`)
```python
def retrieve(query: str, sku_id: str | None, k: int = 3) -> list[Hit]:
    # 1. filter chunks by sku_id when given (plus chunks with no sku_ids = general rules)
    # 2. vector mode: embed query (cache by query string), cosine similarity
    #    bm25 mode: BM25 scores
    # 3. return top-k with score, source, title, chunk_id
```
Query embeddings are cached in-process (`functools.lru_cache`) — the agents use templated queries, so after warm-up there are almost no API calls.

### 2.4 Templated queries (who asks what)
| Trigger | Query |
|---|---|
| Vision scan on SKU | `"{sku_name} storage shelf life refrigerator signs of spoilage"` |
| Cold-chain event | `"{sku_name} temperature abuse shelf life reduction"` |
| Rainstorm / humidity spike | `"{category} high humidity storage effect"` |
| Bundling two SKUs | `"ethylene {sku_a} {sku_b} storage together"` (warn if a producer is boxed with a sensitive item — e.g. bananas/avocados with spinach) |

The RAG agent logs: `Retrieved "Strawberries — refrigerator storage" (USDA FoodKeeper, score 0.82): keep 3–7 days refrigerated; discard if mold…` and puts the full hit in `data` for the expandable log line.

### 2.5 Rules
- Retrieved text **informs the log and citations only**; it never changes numbers in the engine at runtime. Numeric parameters (SL hours, ε, CO₂e factors) are fixed at seed-build time from the same sources.
- Show the source name on everything the RAG agent says.
- Quote short snippets; don't paste whole documents into the UI.
