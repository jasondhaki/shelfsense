"""MCP server `shelfsense-knowledge`: the cited food-handling knowledge base.

uv run python -m app.mcp.knowledge_server            # stdio
uv run python -m app.mcp.knowledge_server --http     # streamable HTTP, :8766/mcp
"""

from mcp.server.mcpserver import MCPServer

from app.agents import explain as explainer
from app.config import get_settings
from app.mcp import serve
from app.models.contracts import ExplainRequest
from app.rag.retriever import RAG, Retriever
from app.sim.cli import SEED_DIR

server = MCPServer(
    "shelfsense-knowledge",
    instructions="Food storage, shelf-life, ethylene and retail-waste knowledge from USDA "
    "FoodKeeper, UC Davis, USDA AMS, Open Food Facts and FAO. Always cite the source field.",
)
_r: Retriever | None = None


def retriever() -> Retriever:
    global _r
    if _r is None:
        s = get_settings()
        _r = Retriever("bm25", embed_model=s.gemini_embed_model)  # offline, no API calls
    return _r


@server.tool()
def search_knowledge(query: str, sku_id: str | None = None, k: int = 3) -> list[dict]:
    """Keyword (BM25 over contextualised chunks) search; sku_id (e.g. STRW-01) narrows to that
    product plus general guidance. Returns source, title, url, text, score."""
    return [h.as_dict() for h in retriever().retrieve(query, sku_id, max(1, min(k, 10)))]


@server.tool()
def product_graph(sku_id: str) -> dict:
    """Knowledge-graph facts for a product: category, shelf life, ethylene class and clashes,
    and which sources describe it."""
    r = retriever()
    return {
        "facts": r.graph_facts(sku_id),
        "clashes_with": [
            n.removeprefix("sku:") for n in r.neighbours(f"sku:{sku_id}", "CLASHES_WITH")
        ],
    }


@server.tool()
async def explain_decision(agent: str, message: str) -> dict:
    """Plain-language, cited explanation of one ShelfSense agent log line (agent is e.g.
    PRICING_AGENT). Uses the configured LLM, or template text when none is set."""
    req = ExplainRequest(agent=agent, message=message)  # validates the agent tag
    return (await explainer.explain(req, retriever(), get_settings())).model_dump()


@server.resource("shelfsense://credits", mime_type="text/markdown")
def credits() -> str:
    """Data sources, licences and retrieval dates."""
    return (SEED_DIR / "CREDITS.md").read_text(encoding="utf-8")


@server.resource("shelfsense://graph", mime_type="application/json")
def graph() -> str:
    """The whole knowledge graph (nodes + typed edges)."""
    return (RAG / "graph.json").read_text(encoding="utf-8")


if __name__ == "__main__":
    serve(server, 8766)
