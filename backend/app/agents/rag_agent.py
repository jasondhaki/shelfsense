"""RAG_KNOWLEDGE_AGENT — stub until Phase 7 (retriever + citations)."""

from app.sim.state import LogDraft, SimState


def on_event(state: SimState, event: dict) -> LogDraft | None:
    if event["type"] not in ("rainstorm", "cold_chain_delay", "vision_override"):
        return None
    return LogDraft(
        event["tick"],
        "RAG_KNOWLEDGE_AGENT",
        "info",
        f"Knowledge retrieval for {event['type']} not yet implemented (Phase 7)",
    )
