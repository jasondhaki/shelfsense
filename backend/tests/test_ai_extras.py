"""Explain endpoint (template + guardrail), graph RAG, retrieval eval, report API, MCP servers."""

import asyncio

from fastapi.testclient import TestClient

from app.agents import explain
from app.config import Settings
from app.main import app
from app.mcp import knowledge_server, sim_server
from app.models.contracts import ExplainRequest
from app.rag.retriever import Retriever
from scripts.eval_rag import evaluate

MSG = "STRW-01 markdown 35% → $3.89 (velocity gap 4.2 units/h, RSL 19 h)"


def test_graph_facts_and_clash_expansion():
    r = Retriever("bm25")
    facts = " ".join(r.graph_facts("SPIN-01"))
    assert "ethylene-sensitive" in facts and "Hass Avocado" in facts
    ids = [h.chunk_id for h in r.graph_retrieve("spinach storage", "SPIN-01", k=2)]
    assert any(i.startswith("ethylene_") and "SPIN" not in i for i in ids)  # hop to a producer


def test_retrieval_eval_floor():
    m = evaluate(Retriever("bm25"))
    assert m["hit@3"] >= 0.9 and m["mrr"] >= 0.8


def test_numbers_guardrail():
    ctx = "markdown 35% at RSL 19 h, ratio 0.35"
    assert explain.numbers_grounded("A 35% markdown with 19 hours left.", ctx)
    assert not explain.numbers_grounded("Price drops to $2.10.", ctx)


def test_explain_template_and_rejected_llm(monkeypatch):
    req = ExplainRequest(agent="PRICING_AGENT", message=MSG)
    r = Retriever("bm25")
    out = asyncio.run(explain.explain(req, r, Settings(llm_provider="none")))
    assert out.mode == "template" and out.citations and out.facts

    async def invents(*_a, **_k):
        return "Strawberries were cut to $1.00 because of 99 hours."

    monkeypatch.setattr(explain.llm, "generate", invents)
    s = Settings(llm_provider="ollama", ollama_model="qwen2.5:3b")
    out = asyncio.run(explain.explain(req, r, s))
    assert out.mode == "template" and out.guardrail

    async def grounded(*_a, **_k):
        return "Store B cut strawberries 35% because only 19 h of shelf life were left."

    monkeypatch.setattr(explain.llm, "generate", grounded)
    out = asyncio.run(explain.explain(req.model_copy(update={"message": MSG + " "}), r, s))
    assert out.mode == "llm" and out.provider == "ollama" and out.guardrail is None


def test_explain_and_report_routes():
    with TestClient(app) as c:
        e = c.post("/api/explain", json={"agent": "PRICING_AGENT", "message": MSG})
        assert e.status_code == 200 and e.json()["citations"]
        assert c.post("/api/explain", json={"agent": "NOPE", "message": "x"}).status_code == 422
        rep = c.get("/api/report", params={"seed": 42, "scenario": "demo"}).json()
        assert len(rep["daily"]) == 7 and rep["kpis"]["waste_reduction_pct"] is not None
        assert c.get("/api/report", params={"hours": 999}).status_code == 422


def test_mcp_servers_list_and_call_tools():
    async def go():
        sim = {t.name for t in await sim_server.server.list_tools()}
        kb = {t.name for t in await knowledge_server.server.list_tools()}
        assert {"run_week", "benchmark", "list_skus", "price_formula"} <= sim
        assert {"search_knowledge", "product_graph", "explain_decision"} <= kb
        res = await knowledge_server.server.call_tool("search_knowledge", {"query": "spinach"})
        assert "UC Davis" in str(res)

    asyncio.run(go())
    assert sim_server.run_week(42, "demo", 24)["hours"] == 24
    assert sim_server.price_formula("STRW-01", hour=30)["sku_id"] == "STRW-01"


def test_vision_and_demand_mcp_servers():
    from app.mcp import demand_server, vision_server

    frames = vision_server.list_frames()
    assert {f["frame_id"] for f in frames} == {"frame1", "frame2", "frame3"}
    g = vision_server.grade_frame("frame1")
    assert g["source"] == "fixture" and 1.0 <= g["alpha_vision"] <= 3.0
    f = demand_server.demand_forecast("STRW-01", from_hour=0, hours=24)
    assert len(f["hourly"]) == 24 and f["total_units"] > 0
    assert demand_server.demand_forecast("STRW-01", 0, 24) == f  # deterministic


def test_warehouse_mcp_is_read_only(tmp_path, monkeypatch):
    import pytest

    duckdb = pytest.importorskip("duckdb")
    from app.mcp import warehouse_server

    db = tmp_path / "w.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE TABLE runs AS SELECT 1 AS seed, 50.0 AS waste_reduction_pct")
    monkeypatch.setattr(warehouse_server, "DB", db)
    assert warehouse_server.query("SELECT seed FROM runs")["rows"] == [(1,)]
    assert "runs" in warehouse_server.tables()
    for bad in ("DROP TABLE runs", "SELECT 1; DROP TABLE runs", "SELECT * FROM read_csv('x.csv')"):
        with pytest.raises((ValueError, duckdb.Error)):
            warehouse_server.query(bad)
