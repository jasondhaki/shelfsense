"""Runs one tick: the pure engine (which already runs the DEMAND / PRICING / PROCUREMENT /
bundling phases in SIMULATION_ENGINE §10 order and writes their log lines), then the
knowledge agents that react to what happened.

Demand/pricing/procurement log templates live next to their math in app/sim so a message can
never disagree with the number it explains (see ARCHITECTURE decisions log)."""

from app.agents import rag_agent
from app.agents.bus import AgentBus
from app.models.contracts import LogEntry
from app.sim import engine
from app.sim.events import Event
from app.sim.state import SimState


class Orchestrator:
    def __init__(self, bus: AgentBus) -> None:
        self.bus = bus

    def step(self, state: SimState, events: list[Event]) -> tuple[SimState, list[LogEntry]]:
        tick = state.tick
        state, drafts = engine.step(state, events)
        applied = [e for e in state.event_log if e["tick"] == tick]
        drafts += [d for e in applied if (d := rag_agent.on_event(state, e)) is not None]
        return state, self.bus.publish(drafts)
