"""REST routes (BACKEND §3). Validation only; behaviour lives in the controller."""

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app import views
from app.agents import vision_agent
from app.config import get_settings
from app.controller import EventRejected, SimController
from app.models.contracts import (
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
    return request.app.state.controller


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
