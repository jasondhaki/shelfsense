"""VISION_AGENT: image -> VisionExtraction -> α_vision -> queued vision_override (AI_PIPELINE §1).

Modes: cached (fixture per preset frame, default) or live (Gemini). Live failures fall back to the
fixture for preset frames; a custom image with no live result is a clear 422. The shelf-life
change is only *previewed* here; the engine applies it at the start of the next tick."""

from pathlib import Path

from app.config import Settings
from app.controller import EventRejected, SimController
from app.models.contracts import Citation, VisionExtraction, VisionScanResult
from app.services import gemini
from app.sim.shelf_life import alpha_from_vision, beta_sku, printed_remaining, rsl_known

DATA = Path(__file__).resolve().parents[2] / "data"
FIXTURES = DATA / "fixtures" / "vision"
CORPUS = DATA / "rag" / "corpus"
LABEL_TO_SKU = {
    "strawberries": "STRW-01",
    "bananas": "BANA-01",
    "avocados": "AVOC-01",
    "spinach": "SPIN-01",
    "cherry_tomatoes": "TOMA-01",
    "sourdough": "SOUR-01",
    "salmon": "SALM-01",
    "milk": "MILK-01",
}


class ScanFailed(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def fixture(frame_id: str) -> VisionExtraction:
    return VisionExtraction.model_validate_json((FIXTURES / f"{frame_id}.json").read_text("utf-8"))


def foodkeeper_citation(sku_id: str) -> Citation | None:
    """Direct FoodKeeper lookup for the SKU (Phase 7 replaces this with RAG retrieval)."""
    f = CORPUS / f"foodkeeper_{sku_id}.md"
    if not f.exists():
        return None
    head, _, body = f.read_text(encoding="utf-8").partition("---\n")[2].partition("---\n")
    meta = dict(line.split(": ", 1) for line in head.splitlines() if ": " in line)
    return Citation(
        source=meta.get("source", "USDA FoodKeeper"),
        title=meta.get("title", sku_id),
        chunk_id=f.stem,
        text=body.strip()[:400],
    )


async def scan(
    ctl: SimController,
    settings: Settings,
    frame_id: str | None,
    image: bytes | None,
    mime: str | None,
    sku_hint: str | None,
) -> VisionScanResult:
    note = None
    extraction: VisionExtraction | None = None
    mode = "cached"
    if settings.vision_mode == "live" and gemini.live_ready(settings) and image and mime:
        extraction = await gemini.extract(image, mime, settings)
        if extraction is not None:
            mode = "live"
        elif frame_id:
            note = "Live vision failed or timed out; showing the cached result for this frame."
    elif image and not frame_id:
        raise ScanFailed(
            422,
            "Custom images need live vision. Set VISION_MODE=live, "
            "GEMINI_API_KEY and GEMINI_VISION_MODEL, or pick a preset frame.",
        )
    if extraction is None:
        if not frame_id:
            raise ScanFailed(
                422,
                "The vision model couldn't read this image. Try a clearer, "
                "well-lit photo of produce on a shelf.",
            )
        extraction = fixture(frame_id)

    state = ctl.state
    sku_id = sku_hint or LABEL_TO_SKU.get(extraction.primary_sku_label)
    alpha = alpha_from_vision(extraction.visual_quality_score, extraction.defects_detected)
    result = VisionScanResult(
        frame_id=frame_id or "custom",
        mode=mode,
        extraction=extraction,
        target_sku=sku_id,
        alpha_vision=round(alpha, 3),
        rsl_before_hours=None,
        printed_remaining_hours=None,
        rsl_after_hours=None,
        foodkeeper_citation=None,
        applied_at_tick=None,
        note=note,
    )
    if sku_id is None:  # "other": show the extraction, change nothing
        result.note = note or "No ShelfSense product recognised; shelf life unchanged."
        return result

    sku = state.config.sku_by_id[sku_id]
    batches = state.b.batches[sku_id]
    if batches:
        oldest = batches[0]
        beta = beta_sku(state.beta_env, sku.weather_exposure)
        result.rsl_before_hours = round(rsl_known(oldest, beta), 1)
        result.printed_remaining_hours = round(
            printed_remaining(oldest, sku.sl_nominal_hours, state.tick), 1
        )
        # preview of what the engine will apply: same batch, observed α, truth now known
        result.rsl_after_hours = round(
            max(0.0, (oldest.sl_true - oldest.age_true) / (alpha * beta)), 1
        )
    result.foodkeeper_citation = foodkeeper_citation(sku_id)

    payload = {
        "sku_id": sku_id,
        "alpha": round(alpha, 3),
        "frame_id": result.frame_id,
        "mode": mode,
        "quality": extraction.visual_quality_score,
        "defects": extraction.defects_detected,
        "rsl_before_h": result.rsl_before_hours,
        "rsl_after_h": result.rsl_after_hours,
        "citation": result.foodkeeper_citation.model_dump() if result.foodkeeper_citation else None,
    }
    try:
        result.applied_at_tick = ctl.queue_event("vision_override", payload)
    except EventRejected as e:
        result.note = f"Not applied: {e}"
    return result
