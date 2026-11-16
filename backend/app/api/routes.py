"""REST routes (BACKEND §3). Validation only; behaviour lives in the controller."""

import csv
import io

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile

from app import views
from app.agents import vision_agent
from app.config import get_settings
from app.controller import EventRejected, SimController
from app.models.contracts import (
    ArchEdge,
    Architecture,
    ArchNode,
    ControlRequest,
    ControlResponse,
    EventRequest,
    EventResponse,
    FormulaBreakdown,
    SimSnapshot,
    VisionScanResult,
    WeatherNow,
)

router = APIRouter(prefix="/api")


def ctl(request: Request) -> SimController:
    return request.app.state.sessions.get(request.headers.get("x-session-id"))


@router.get("/sim/state", response_model=SimSnapshot)
def sim_state(request: Request) -> SimSnapshot:
    return ctl(request).snapshot()


@router.post("/sim/control", response_model=ControlResponse)
async def sim_control(body: ControlRequest, request: Request) -> ControlResponse:
    return await ctl(request).control(body.action, body.seed, body.replay, body.scenario)


@router.post("/sim/events", response_model=EventResponse)
def sim_events(body: EventRequest, request: Request) -> EventResponse:
    try:
        tick = ctl(request).queue_event(body.type, body.payload)
    except EventRejected as e:
        raise HTTPException(409, str(e)) from None
    return EventResponse(queued=True, apply_at_tick=tick)


@router.get("/sim/skus/{sku_id}/formula", response_model=FormulaBreakdown)
def sku_formula(sku_id: str, request: Request) -> FormulaBreakdown:
    c = ctl(request)
    sku = c.state.config.sku_by_id.get(sku_id)
    if sku is None:
        raise HTTPException(404, f"Unknown SKU {sku_id}")
    return views.formula(c.state, sku)


@router.get("/meta/weather", response_model=WeatherNow)
async def meta_weather(request: Request) -> WeatherNow:
    c = ctl(request)
    await c.noaa.refresh()
    return c.weather()


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAGIC = {b"\xff\xd8\xff": "image/jpeg", b"\x89PNG\r\n\x1a\n": "image/png"}
FRAMES = {"frame1", "frame2", "frame3"}


@router.post("/vision/scan", response_model=VisionScanResult)
async def vision_scan(
    request: Request,
    frame_id: str | None = Form(None),
    file: UploadFile | None = File(None),
    sku_hint: str | None = Form(None),
) -> VisionScanResult:
    c = ctl(request)
    if frame_id is not None and frame_id not in FRAMES:
        raise HTTPException(422, f"Unknown frame {frame_id!r}; use frame1, frame2 or frame3.")
    if frame_id is None and file is None:
        raise HTTPException(422, "Send a preset frame_id or an image file.")
    if sku_hint is not None and sku_hint not in c.state.config.sku_by_id:
        raise HTTPException(422, f"Unknown SKU {sku_hint!r}.")
    image = mime = None
    if file is not None:
        image = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(image) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Image is larger than 5 MB.")
        mime = next((m for sig, m in MAGIC.items() if image.startswith(sig)), None)
        if mime is None:
            raise HTTPException(422, "Only JPG or PNG images are accepted.")
    try:
        return await vision_agent.scan(c, get_settings(), frame_id, image, mime, sku_hint)
    except vision_agent.ScanFailed as e:
        raise HTTPException(e.status, str(e)) from None


@router.get("/meta/architecture", response_model=Architecture)
def meta_architecture(request: Request) -> Architecture:
    c = ctl(request)
    s = get_settings()
    vision_live = s.vision_mode == "live" and bool(s.gemini_api_key and s.gemini_vision_model)
    vector = c.retriever.mode == "vector"
    noaa_live = c.noaa.source == "live"
    n = ArchNode
    nodes = [
        n(
            id="usda",
            label="USDA FoodKeeper",
            layer="source",
            status="static",
            detail="Shelf-life ranges, merged into seed data",
        ),
        n(
            id="off",
            label="Open Food Facts",
            layer="source",
            status="static",
            detail="Nutri-Score, packaging (6 barcodes)",
        ),
        n(
            id="noaa",
            label="Open-Meteo weather" if s.weather_provider == "open_meteo" else "NOAA weather",
            layer="source",
            status="live" if noaa_live else "fallback",
            detail="Live forecast" if noaa_live else "Committed snapshot",
        ),
        n(
            id="kaggle",
            label="Kaggle Favorita",
            layer="source",
            status="static",
            detail="Weekday demand patterns (aggregates)",
        ),
        n(
            id="fao",
            label="FAO + Poore & Nemecek",
            layer="source",
            status="static",
            detail="Retail waste %, CO2e factors",
        ),
        n(
            id="seed",
            label="Seed data",
            layer="knowledge",
            status="static",
            detail="skus.json, sales profile, weather, FAO",
        ),
        n(
            id="rag",
            label="RAG index",
            layer="knowledge",
            status="live" if vector else "fallback",
            detail="Gemini embeddings"
            if vector
            else f"BM25 keyword search ({len(c.retriever.chunks)} chunks)",
        ),
        n(
            id="vision",
            label="Vision agent",
            layer="agent",
            status="live" if vision_live else "fallback",
            detail="Gemini multimodal" if vision_live else "Cached fixtures",
            agent="VISION_AGENT",
        ),
        n(
            id="rag_agent",
            label="RAG knowledge agent",
            layer="agent",
            status="live",
            detail="Cites FoodKeeper, UC Davis, USDA AMS, FAO",
            agent="RAG_KNOWLEDGE_AGENT",
        ),
        n(
            id="demand",
            label="Demand agent",
            layer="agent",
            status="live",
            detail="Hourly forecast x weather",
            agent="DEMAND_AGENT",
        ),
        n(
            id="pricing",
            label="Pricing agent",
            layer="agent",
            status="live",
            detail="Velocity gap -> elasticity markdown, boxes",
            agent="PRICING_AGENT",
        ),
        n(
            id="procurement",
            label="Procurement agent",
            layer="agent",
            status="live",
            detail="Throttled next-delivery POs",
            agent="PROCUREMENT_AGENT",
        ),
        n(
            id="orchestrator",
            label="Orchestrator + engine",
            layer="core",
            status="live",
            detail=f"Deterministic tick loop, seed {c.seed}",
            agent="SYSTEM",
        ),
        n(id="esl", label="Shelf labels", layer="output", status="live", detail="8 ESL prices"),
        n(
            id="po",
            label="Purchase orders",
            layer="output",
            status="live",
            detail="Next deliveries",
        ),
        n(id="boxes", label="Surplus boxes", layer="output", status="live", detail="Flash bundles"),
    ]
    pairs = [
        ("usda", "seed"),
        ("off", "seed"),
        ("kaggle", "seed"),
        ("fao", "seed"),
        ("noaa", "seed"),
        ("usda", "rag"),
        ("off", "rag"),
        ("fao", "rag"),
        ("seed", "demand"),
        ("seed", "pricing"),
        ("seed", "procurement"),
        ("rag", "rag_agent"),
        ("vision", "orchestrator"),
        ("rag_agent", "orchestrator"),
        ("demand", "orchestrator"),
        ("pricing", "orchestrator"),
        ("procurement", "orchestrator"),
        ("orchestrator", "esl"),
        ("orchestrator", "po"),
        ("orchestrator", "boxes"),
    ]
    return Architecture(nodes=nodes, edges=[ArchEdge(source=a, target=b) for a, b in pairs])


@router.get("/sim/report.csv")
def sim_report(request: Request) -> Response:
    """Hourly series of this session's run (backlog: export run report)."""
    c = ctl(request)
    s = c.state
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "tick",
            "sim_time",
            "waste_kg_baseline",
            "waste_kg_shelfsense",
            "revenue_usd_baseline",
            "revenue_usd_shelfsense",
        ]
    )
    for p in s.chart:
        t = p["tick"]
        w.writerow(
            [
                t,
                f"D{t // 24 + 1} {t % 24:02d}:00",
                round(p["waste_kg_a"], 3),
                round(p["waste_kg_b"], 3),
                round(p["revenue_a"], 2),
                round(p["revenue_b"], 2),
            ]
        )
    k = views.kpis(s)
    w.writerow([])
    for name, value in k.model_dump().items():
        w.writerow([name, "" if value is None else round(value, 3)])
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="shelfsense-seed{c.seed}-t{s.tick}.csv"'
        },
    )
