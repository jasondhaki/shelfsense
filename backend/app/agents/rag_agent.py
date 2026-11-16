"""RAG_KNOWLEDGE_AGENT (AI_PIPELINE §2). Retrieves cited knowledge for events and box building.
Retrieved text informs the log and citations only — it never changes engine numbers."""

from app.rag.retriever import Hit, Retriever
from app.sim.state import LogDraft, SimConfig, SimState

# Plain produce nouns: full product names ("Organic Strawberries 1 lb") over-match the
# product-metadata chunks, so the templated queries use what a handling guide would say.
NOUN = {
    "STRW-01": "strawberries",
    "BANA-01": "bananas",
    "SALM-01": "salmon fish",
    "MILK-01": "milk",
    "SOUR-01": "bread",
    "AVOC-01": "avocados",
    "SPIN-01": "spinach",
    "TOMA-01": "tomatoes",
}
# knowledge sources (excludes barcode metadata, which answers "what is it", not "how to handle it")
KNOWLEDGE = {
    "USDA FoodKeeper",
    "UC Davis Postharvest Center",
    "USDA AMS",
    "ShelfSense ethylene table",
    "ShelfSense model (assumed)",
    "FAO",
}
HUMID_EXPOSURE = 0.8  # rainstorm query covers products at least this exposed


def q_vision(sku: str) -> str:
    return f"{NOUN[sku]} storage shelf life refrigerator signs of spoilage"


def q_cold_chain(sku: str) -> str:
    return f"{NOUN[sku]} temperature abuse shelf life reduction"


def q_humidity(sku: str) -> str:
    return f"{NOUN[sku]} high humidity storage effect"


def q_ethylene(a: str, b: str) -> str:
    return f"ethylene {NOUN[a]} {NOUN[b]} storage together"


def all_queries(cfg: SimConfig) -> list[str]:
    """Every templated query, for warming the vector cache at startup."""
    ids = [s.sku_id for s in cfg.skus if s.sku_id in NOUN]
    out = [f(s) for s in ids for f in (q_vision, q_cold_chain, q_humidity)]
    eth = {s.sku_id: s.off.get("ethylene") for s in cfg.skus}
    # only producer/sensitive pairs are ever queried (box clashes), in both orders
    clash = [(a, b) for a in ids for b in ids if {eth[a], eth[b]} == {"producer", "sensitive"}]
    return out + [q_ethylene(a, b) for a, b in clash]


def vision_citation(r: Retriever, sku: str) -> Hit | None:
    hits = r.retrieve(q_vision(sku), sku, k=1, sources={"USDA FoodKeeper"})
    return hits[0] if hits else None


def _line(tick: int, hit: Hit, level: str = "info", why: str = "") -> LogDraft:
    text = hit.text.replace("\n", " ")
    snippet = text[:140].rstrip() + ("…" if len(text) > 140 else "")
    return LogDraft(
        tick,
        "RAG_KNOWLEDGE_AGENT",
        level,
        f'{why}Retrieved "{hit.title}" ({hit.source}, {hit.mode} {hit.score:.2f}): {snippet}',
        hit.as_dict(),
    )


def on_event(r: Retriever, state: SimState, event: dict) -> list[LogDraft]:
    tick, kind, p = event["tick"], event["type"], event["payload"]
    if kind == "vision_override" and p.get("citation"):
        c = p["citation"]
        hit = Hit(
            c["chunk_id"],
            c["source"],
            c["title"],
            c.get("url", ""),
            (),
            c["text"],
            c.get("score") or 0.0,
            c.get("mode") or "bm25",
        )
        return [_line(tick, hit, why=f"{p['sku_id']}: ")]
    if kind == "cold_chain_delay":
        skus = [s for s in (p.get("skus") or ["STRW-01", "SPIN-01", "SALM-01"]) if s in NOUN]
        out = []
        for s in skus[:3]:
            hits = r.retrieve(q_cold_chain(s), s, k=1, sources=KNOWLEDGE)
            if hits:
                out.append(_line(tick, hits[0], "warn", f"{s}: "))
        return out
    if kind == "rainstorm":
        exposed = [
            s.sku_id
            for s in state.config.skus
            if s.weather_exposure >= HUMID_EXPOSURE and s.sku_id in NOUN
        ]
        hits = r.retrieve(q_humidity(exposed[0]), None, k=1, sources=KNOWLEDGE) if exposed else []
        if hits:
            return [_line(tick, hits[0], "info", f"{len(exposed)} humidity-exposed products: ")]
    return []


def on_drafts(r: Retriever, drafts: list[LogDraft]) -> list[LogDraft]:
    """React to engine lines: cite why boxes keep ethylene producers away from sensitive items."""
    out = []
    for d in drafts:
        data = d.data or {}
        clash = [tuple(x) for x in data.get("ethylene_clash", [])]
        pairs = clash + [tuple(x) for x in data.get("ethylene_avoided", [])]
        if not pairs:
            continue
        a, b = pairs[0]
        hits = r.retrieve(q_ethylene(a, b), None, k=1, sources=KNOWLEDGE)
        if hits:
            level = "warn" if clash else "info"
            out.append(_line(d.tick, hits[0], level, f"{data.get('box_id', 'box')} {a}/{b}: "))
    return out
