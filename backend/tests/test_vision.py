"""Vision pipeline: cached fixtures, upload validation, live success/failure with a fake Gemini.
No test touches the network."""

import pytest
from fastapi.testclient import TestClient

from app.agents import vision_agent
from app.config import get_settings
from app.main import app
from app.services import gemini

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


@pytest.fixture
def client():
    with TestClient(app) as c:
        c.post("/api/sim/control", json={"action": "reset", "seed": 42})
        yield c


@pytest.fixture
def live(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "vision_mode", "live")
    monkeypatch.setattr(s, "gemini_api_key", "test-key")
    monkeypatch.setattr(s, "gemini_vision_model", "test-model")
    return s


def step(c, n=1):
    for _ in range(n):
        c.post("/api/sim/control", json={"action": "step"})


def esl(c, sku):
    return next(e for e in c.get("/api/sim/state").json()["esl"] if e["sku_id"] == sku)


def test_frame3_cached_scan_recalibrates_strawberries(client):
    step(client, 10)
    before = esl(client, "STRW-01")
    r = client.post("/api/vision/scan", data={"frame_id": "frame3"})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "cached" and body["target_sku"] == "STRW-01"
    assert body["alpha_vision"] == pytest.approx(2.35)
    assert body["rsl_after_hours"] < body["rsl_before_hours"]
    assert body["applied_at_tick"] == 10
    assert body["foodkeeper_citation"]["source"] == "USDA FoodKeeper"
    assert {d["severity"] for d in body["extraction"]["detections"]} >= {"clearance_required"}

    step(client)
    s = client.get("/api/sim/state").json()
    lines = [x for x in s["logs"] if x["tick"] == 10]
    assert any(x["agent"] == "VISION_AGENT" and "α_vision 2.35" in x["message"] for x in lines)
    assert any(x["agent"] == "RAG_KNOWLEDGE_AGENT" and "FoodKeeper" in x["message"] for x in lines)
    after = esl(client, "STRW-01")
    assert after["rsl_hours"] < before["rsl_hours"] - 10  # oldest batch now decays 2.5× faster
    assert after["current_price"] <= before["current_price"]


def test_frame1_is_healthy(client):
    body = client.post("/api/vision/scan", data={"frame_id": "frame1"}).json()
    assert body["alpha_vision"] == 1.0 and body["extraction"]["defects_detected"] == []


def test_rejects_bad_input(client):
    assert client.post("/api/vision/scan", data={}).status_code == 422
    assert client.post("/api/vision/scan", data={"frame_id": "frame9"}).status_code == 422
    r = client.post("/api/vision/scan", data={"frame_id": "frame1", "sku_hint": "NOPE"})
    assert r.status_code == 422
    r = client.post("/api/vision/scan", files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 422 and "JPG or PNG" in r.json()["error"]["message"]
    big = JPEG + b"\x00" * (5 * 1024 * 1024)
    r = client.post("/api/vision/scan", files={"file": ("big.jpg", big, "image/jpeg")})
    assert r.status_code == 413 and r.json()["error"]["code"] == "too_large"


def test_custom_upload_needs_live_mode(client):
    r = client.post("/api/vision/scan", files={"file": ("shelf.jpg", JPEG, "image/jpeg")})
    assert r.status_code == 422 and "live vision" in r.json()["error"]["message"]


def test_live_failure_falls_back_to_fixture(client, live, monkeypatch):
    async def broken(*_):
        return None

    monkeypatch.setattr(gemini, "extract", broken)
    r = client.post(
        "/api/vision/scan",
        data={"frame_id": "frame2"},
        files={"file": ("frame2.jpg", JPEG, "image/jpeg")},
    )
    body = r.json()
    assert body["mode"] == "cached" and "cached result" in body["note"]
    assert body["target_sku"] == "BANA-01"
    # a custom image has no fixture to fall back on: friendly 422
    r = client.post("/api/vision/scan", files={"file": ("shelf.jpg", JPEG, "image/jpeg")})
    assert r.status_code == 422 and "couldn't read" in r.json()["error"]["message"]


def test_live_success_uses_model_output(client, live, monkeypatch):
    async def fake(*_):
        return vision_agent.fixture("frame2")

    monkeypatch.setattr(gemini, "extract", fake)
    r = client.post("/api/vision/scan", files={"file": ("shelf.jpg", JPEG, "image/jpeg")})
    body = r.json()
    assert body["mode"] == "live" and body["frame_id"] == "custom"
    assert body["target_sku"] == "BANA-01" and body["alpha_vision"] == pytest.approx(
        1.457, abs=1e-3
    )


def test_gemini_without_key_returns_none():
    import asyncio

    s = get_settings().model_copy(update={"gemini_api_key": ""})
    assert asyncio.run(gemini.extract(JPEG, "image/jpeg", s)) is None
