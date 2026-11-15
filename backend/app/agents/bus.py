"""AgentBus: turns engine LogDrafts into LogEntry objects and keeps a bounded tail."""

from collections import deque

from app.models.contracts import LogEntry
from app.sim.state import LogDraft, sim_time

TAIL = 200  # sent in the hello snapshot so a reconnecting client can refill Zone E


class AgentBus:
    def __init__(self) -> None:
        self.tail: deque[LogEntry] = deque(maxlen=TAIL)

    def publish(self, drafts: list[LogDraft]) -> list[LogEntry]:
        entries = [
            LogEntry(
                tick=d.tick,
                sim_time=sim_time(d.tick),
                agent=d.agent,
                level=d.level,
                message=d.message,
                data=d.data,
            )
            for d in drafts
        ]
        self.tail.extend(entries)
        return entries

    def clear(self) -> None:
        self.tail.clear()
