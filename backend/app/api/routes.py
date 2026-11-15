"""REST routes (BACKEND §3). Validation only; behaviour lives in the controller."""

from fastapi import APIRouter, HTTPException, Request

from app import views
from app.controller import EventRejected, SimController
from app.models.contracts import (
    ControlRequest,
    ControlResponse,
    EventRequest,
    EventResponse,
    FormulaBreakdown,
    SimSnapshot,
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
