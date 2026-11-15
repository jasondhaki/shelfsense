"""SimController: owns the one SimState, the asyncio play loop, the event queue and the
WebSocket fan-out. User events are queued and applied at the start of the next tick, so every
run is reproducible from (seed, event timeline)."""

import asyncio
import contextlib

from app import views
from app.agents.bus import AgentBus
from app.agents.orchestrator import Orchestrator
from app.models.contracts import ControlResponse, SimSnapshot, TickDelta, WeatherNow
from app.services.noaa import NoaaService
from app.sim import engine
from app.sim.cli import demo_timeline, load_config
from app.sim.demand import storm_active
from app.sim.events import Event
from app.sim.state import SimState

SPEEDS = {"play": 1, "fast_forward": 24}  # ticks per second
QUEUE_MAX = 500  # per WebSocket client; oldest message dropped when a client lags


class EventRejected(Exception):
    pass


class SimController:
    def __init__(self, seed: int, noaa: NoaaService) -> None:
        self.noaa = noaa
        self.bus = AgentBus()
        self.orchestrator = Orchestrator(self.bus)
        self.subscribers: set[asyncio.Queue] = set()
        self.lock = asyncio.Lock()
        self.task: asyncio.Task | None = None
        self.speed = 1
        self.playing = False
        self._reset(seed, {})

    # --- state ---------------------------------------------------------------

    def _reset(self, seed: int, timeline: dict[int, list[Event]]) -> None:
        self.seed = seed
        self.state: SimState = engine.new_sim(load_config(seed))
        self.timeline = timeline
        self.queue: list[Event] = []
        self.bus.clear()
        self._last: dict = {}

    @property
    def status(self) -> str:
        if self.state.finished:
            return "finished"
        return "playing" if self.playing else "paused"

    def weather(self) -> WeatherNow:
        w = self.noaa.current()
        return WeatherNow(
            source=self.noaa.source,
            location=w["location"],
            temperature_f=w["temperature_f"],
            precip_probability_pct=w["precip_probability_pct"],
            short_forecast=w["short_forecast"],
            relative_humidity_pct=round(self.state.rh, 1),
            traffic_mult=round(self.state.traffic, 3),
            storm_active=storm_active(self.state, self.state.tick),
        )

    def snapshot(self) -> SimSnapshot:
        s = self.state
        return SimSnapshot(
            tick=s.tick,
            status=self.status,
            speed=self.speed,
            seed=self.seed,
            weather=self.weather(),
            kpis=views.kpis(s),
            esl=views.esl(s),
            po_table=views.po_table(s),
            bundles=views.bundles(s),
            chart=views.chart(s),
            active_events=views.active_events(s),
            logs=list(self.bus.tail),
        )

    def response(self) -> ControlResponse:
        return ControlResponse(status=self.status, tick=self.state.tick, speed=self.speed)

    # --- commands ------------------------------------------------------------

    async def control(
        self,
        action: str,
        seed: int | None = None,
        replay: bool = False,
        scenario: str | None = None,
    ) -> ControlResponse:
        if action in SPEEDS:
            self.speed = SPEEDS[action]
            if not self.state.finished and not self.playing:
                self.playing = True
                self.task = asyncio.create_task(self._loop())
        elif action == "pause":
            await self._stop()
        elif action == "step":
            await self._stop()
            await self._tick()
        elif action == "reset":
            await self._stop()
            if replay:
                timeline: dict[int, list[Event]] = {}
                for e in self.state.event_log:
                    timeline.setdefault(e["tick"], []).append(Event(e["type"], e["payload"]))
            else:
                timeline = demo_timeline() if scenario == "demo" else {}
            self._reset(seed if seed is not None else self.seed, timeline)
            self._broadcast({"type": "hello", "snapshot": self.snapshot().model_dump(mode="json")})
        self._broadcast_status()
        return self.response()

    def queue_event(self, type_: str, payload: dict) -> int:
        s = self.state
        if s.finished:
            raise EventRejected("Simulation finished — reset to inject events.")
        if type_ == "rainstorm" and (
            storm_active(s, s.tick) or any(e.type == "rainstorm" for e in self.queue)
        ):
            raise EventRejected("A rainstorm is already active.")
        if type_ == "cold_chain_delay":
            unknown = [x for x in payload.get("skus", []) if x not in s.config.sku_by_id]
            if unknown:
                raise EventRejected(f"Unknown SKU(s): {', '.join(unknown)}")
        self.queue.append(Event(type_, payload))
        return s.tick

    # --- loop ----------------------------------------------------------------

    async def _loop(self) -> None:
        try:
            while self.playing and not self.state.finished:
                await self._tick()
                await asyncio.sleep(1 / self.speed)
        finally:
            self.playing = False
            self._broadcast_status()

    async def _stop(self) -> None:
        self.playing = False
        if self.task and not self.task.done():
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task
        self.task = None

    async def _tick(self) -> None:
        async with self.lock:
            if self.state.finished:
                return
            events = self.timeline.get(self.state.tick, []) + self.queue
            self.queue = []
            tick = self.state.tick
            self.state, logs = self.orchestrator.step(self.state, events)
            for e in self.state.event_log:
                if e["tick"] == tick:
                    self._broadcast({"type": "event_applied", "event": e})
            self._broadcast(
                {
                    "type": "tick",
                    "tick": self.state.tick,
                    "delta": self._delta().model_dump(mode="json"),
                    "logs": [x.model_dump(mode="json") for x in logs],
                }
            )

    def _delta(self) -> TickDelta:
        s = self.state

        def changed(key: str, value):
            dumped = (
                [v.model_dump() for v in value] if isinstance(value, list) else value.model_dump()
            )
            if self._last.get(key) == dumped:
                return None
            self._last[key] = dumped
            return value

        return TickDelta(
            kpis=views.kpis(s),
            esl=views.esl(s),
            po_table=changed("po", views.po_table(s)),
            bundles=changed("bundles", views.bundles(s)),
            chart_point=views.chart(s)[-1],
            weather=changed("weather", self.weather()),
            active_events=changed("events", views.active_events(s)),
        )

    # --- fan-out -------------------------------------------------------------

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_MAX)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)

    def _broadcast(self, msg: dict) -> None:
        for q in self.subscribers:
            if q.full():
                q.get_nowait()  # ponytail: drop oldest for a lagging client; batch if UI lags
            q.put_nowait(msg)

    def _broadcast_status(self) -> None:
        self._broadcast({"type": "status", "status": self.status, "speed": self.speed})
