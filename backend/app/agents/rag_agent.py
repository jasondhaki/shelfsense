"""RAG_KNOWLEDGE_AGENT — retrieval arrives in Phase 7. Until then: vision scans surface the
FoodKeeper record found by direct lookup (labelled as such); other events log a stub line."""

from app.sim.state import LogDraft, SimState


def on_event(state: SimState, event: dict) -> LogDraft | None:
    tick, kind, payload = event["tick"], event["type"], event["payload"]
    cite = payload.get("citation") if kind == "vision_override" else None
    if cite:
        snippet = cite["text"][:140].rstrip() + ("…" if len(cite["text"]) > 140 else "")
        return LogDraft(
            tick,
            "RAG_KNOWLEDGE_AGENT",
            "info",
            f'"{cite["title"]}" ({cite["source"]}, direct lookup): {snippet}',
            cite,
        )
    if kind in ("rainstorm", "cold_chain_delay", "vision_override"):
        return LogDraft(
            tick,
            "RAG_KNOWLEDGE_AGENT",
            "info",
            f"Knowledge retrieval for {kind} not yet implemented (Phase 7)",
        )
    return None
