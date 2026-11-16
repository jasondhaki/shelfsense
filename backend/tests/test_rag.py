"""RAG retrieval (BM25 + vector with fake embeddings), event citations, ethylene-aware boxes."""

import asyncio
import shutil

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.agents import rag_agent
from app.main import app
from app.rag.retriever import RAG, Retriever
from app.sim import bundling, engine
from app.sim.cli import load_config
from app.sim.state import Batch


@pytest.fixture(scope="module")
def r():
    return Retriever("bm25")


def test_bm25_returns_foodkeeper_strawberry_chunk(r):
    hit = rag_agent.vision_citation(r, "STRW-01")
    assert hit is not None and hit.chunk_id == "foodkeeper_STRW-01#0"
    assert hit.source == "USDA FoodKeeper" and hit.mode == "bm25"
    top = r.retrieve(rag_agent.q_vision("STRW-01"), "STRW-01", k=3)
    assert "foodkeeper_STRW-01#0" in [h.chunk_id for h in top]


def test_sku_filter_and_determinism(r):
    hits = r.retrieve("spinach storage", "SPIN-01", k=10)
    assert all(not h.sku_ids or "SPIN-01" in h.sku_ids for h in hits)
    assert [h.chunk_id for h in hits] == [
        h.chunk_id for h in r.retrieve("spinach storage", "SPIN-01", k=10)
    ]
    assert r.retrieve("zzzz qqqq", None) == []


def test_every_event_logs_a_cited_source():
    with TestClient(app) as c:
        c.post("/api/sim/control", json={"action": "reset", "seed": 42})
        c.post("/api/sim/events", json={"type": "rainstorm"})
        c.post("/api/sim/events", json={"type": "cold_chain_delay"})
        c.post("/api/vision/scan", data={"frame_id": "frame3"})
        c.post("/api/sim/control", json={"action": "step"})
        logs = [
            x for x in c.get("/api/sim/state").json()["logs"] if x["agent"] == "RAG_KNOWLEDGE_AGENT"
        ]
    assert len(logs) >= 5  # 1 humidity + 3 cold-chain + 1 vision
    for x in logs:
        assert x["data"]["source"] and x["data"]["chunk_id"] and "Retrieved" in x["message"]
    assert any("UC Davis" in x["message"] for x in logs)  # spinach cold-chain handling
    assert any(
        "USDA FoodKeeper" in x["message"] and x["message"].startswith("STRW-01") for x in logs
    )


def _bundle_state(skus):
    state = engine.new_sim(load_config(1))
    for sid in state.config.sku_by_id:
        state.b.batches[sid] = []
    for sid in skus:
        sku = state.config.sku_by_id[sid]
        b = Batch(
            f"{sid}-old", sid, 1, 0, sl_true=sku.sl_nominal_hours, sl_known=sku.sl_nominal_hours
        )
        b.age_true = b.age_known = sku.sl_nominal_hours - 2  # 2 h left
        state.b.batches[sid] = [b]
        state.pricing[sid] = {"floor_bound": True}
    state.tick = 23  # store closed: no expected sales, so every unit is excess
    return state


def test_box_swaps_away_from_ethylene_clash():
    state = _bundle_state(["SPIN-01", "AVOC-01", "SALM-01"])
    drafts = bundling.build_boxes(state, state.tick)
    box = state.b.boxes[0]
    assert {i.sku_id for i in box.items} == {"SPIN-01", "SALM-01"}  # avocado kept away from spinach
    assert drafts[0].data["ethylene_clash"] == []
    lines = rag_agent.on_drafts(Retriever("bm25"), drafts)
    assert lines and lines[0].agent == "RAG_KNOWLEDGE_AGENT"


def test_unavoidable_clash_is_flagged():
    state = _bundle_state(["SPIN-01", "AVOC-01"])
    drafts = bundling.build_boxes(state, state.tick)
    assert drafts[0].level == "warn" and drafts[0].data["ethylene_clash"] == [
        ["AVOC-01", "SPIN-01"]
    ]
    lines = rag_agent.on_drafts(Retriever("bm25"), drafts)
    assert lines[0].level == "warn" and "Spinach" in lines[0].message


def test_vector_mode_with_fake_embeddings(tmp_path):
    for f in ("chunks.json", "bm25.json"):
        shutil.copy(RAG / f, tmp_path / f)
    base = Retriever("bm25", rag_dir=tmp_path)
    ids = [c["id"] for c in base.chunks]
    vecs = np.eye(len(ids), dtype="float32")
    np.savez(tmp_path / "index.npz", embeddings=vecs, ids=np.array(ids))
    target = ids.index("ucdavis_spinach#0")

    async def fake_embed(qs):
        return np.stack([vecs[target] for _ in qs])

    r = Retriever("auto", vector_ready=True, rag_dir=tmp_path)
    assert r.mode == "vector"
    asyncio.run(r.warm(["anything"], fake_embed))
    hit = r.retrieve("anything", None, k=1)[0]
    assert hit.chunk_id == "ucdavis_spinach#0" and hit.mode == "vector"
    assert r.retrieve("never warmed spinach", None, k=1)[0].mode == "bm25"  # uncached → BM25

    async def broken(qs):
        return None

    r2 = Retriever("vector", rag_dir=tmp_path)
    asyncio.run(r2.warm(["x"], broken))
    assert r2.mode == "bm25"  # embedding failure degrades, never breaks
    assert Retriever("vector", rag_dir=RAG).mode in ("bm25", "vector")
