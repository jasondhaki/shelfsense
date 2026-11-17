"""Plain-language explanation of one agent log line (AI_PIPELINE §3).

RAG-grounded: the prompt holds the log line, its data, knowledge-graph facts and the top
retrieved chunks (graph-expanded). The LLM only writes text; it sets no price, RSL or order.
Guardrail: every number in the answer must appear in that context, otherwise the template
answer is shown instead and the reason is returned."""

import hashlib
import json
import re
from pathlib import Path

from app.agents.rag_agent import KNOWLEDGE, NOUN
from app.config import Settings
from app.models.contracts import Citation, ExplainRequest, Explanation
from app.rag.retriever import Retriever
from app.services import llm

SYSTEM = (Path(__file__).parent / "prompts" / "explain.txt").read_text(encoding="utf-8")
SKU = re.compile(r"\b[A-Z]{4}-\d{2}\b")
NUM = re.compile(r"\d+(?:[.,]\d+)*")
DATA_CHARS = 1200  # token budget: log data is trimmed, snippets are already ~250 chars each
TOPIC = {
    "PRICING_AGENT": "shelf life storage spoilage",
    "PROCUREMENT_AGENT": "storage shelf life waste",
    "DEMAND_AGENT": "high humidity storage effect",
    "VISION_AGENT": "signs of spoilage storage",
}
_cache: dict[str, Explanation] = {}  # deterministic inputs → reuse answers, no repeat calls


def sku_of(req: ExplainRequest) -> str | None:
    sid = (req.data or {}).get("sku_id")
    if isinstance(sid, str) and sid in NOUN:
        return sid
    m = SKU.search(req.message)
    return m.group(0) if m and m.group(0) in NOUN else None


def _nums(text: str) -> set[str]:
    out = set()
    for raw in NUM.findall(text):
        try:
            x = float(raw.replace(",", ""))
        except ValueError:
            continue
        out |= {f"{x:g}", f"{x * 100:g}", f"{x / 100:g}", f"{round(x):g}"}
    return out


def numbers_grounded(answer: str, context: str) -> bool:
    """True when each number in the answer (as written, or as a % of a fraction) is in context."""
    allowed = _nums(context)
    return all(f"{float(n.replace(',', '')):g}" in allowed for n in NUM.findall(answer))


def template(req: ExplainRequest, facts: list[str], hits: list) -> str:
    out = [f"The {req.agent.replace('_', ' ').lower()} logged: {req.message}"]
    out += facts[:2]
    if hits:
        out.append(f"Background ({hits[0].source}): {hits[0].text[:220].rstrip()}")
    return " ".join(out)


async def explain(req: ExplainRequest, r: Retriever, s: Settings) -> Explanation:
    key = hashlib.sha256(
        json.dumps([req.model_dump(), llm.target(s)], sort_keys=True, default=str).encode()
    ).hexdigest()
    if key in _cache:
        return _cache[key]
    sku = sku_of(req)
    facts = r.graph_facts(sku) if sku else []
    query = f"{NOUN[sku] if sku else ''} {TOPIC.get(req.agent, 'storage shelf life')}".strip()
    hits = [h for h in r.graph_retrieve(query, sku, k=3) if h.source in KNOWLEDGE][:4]
    data = json.dumps(req.data, default=str)[:DATA_CHARS] if req.data else "none"
    context = "\n".join(
        [f"DECISION ({req.agent}): {req.message}", f"DATA: {data}", "GRAPH FACTS:"]
        + [f"- {f}" for f in facts]
        + ["SNIPPETS:"]
        + [f"[{i}] {h.source} - {h.title}: {h.text}" for i, h in enumerate(hits, 1)]
    )
    answer = await llm.generate(SYSTEM, context, s)
    target = llm.target(s)
    guard = None
    if answer and not numbers_grounded(answer, context):
        guard, answer = "The model's answer had a number that is not in the log or sources.", None
    out = Explanation(
        text=answer or template(req, facts, hits),
        mode="llm" if answer else "template",
        provider=target[0] if answer and target else None,
        model=target[1] if answer and target else None,
        guardrail=guard,
        facts=facts,
        citations=[Citation(**h.as_dict()) for h in hits],
    )
    if answer or guard or target is None:  # a failed call is retried next time, not cached
        if len(_cache) > 512:
            _cache.clear()
        _cache[key] = out
    return out
