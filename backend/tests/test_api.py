"""REST + WebSocket contract tests. Drive the sim with `step` — no sleeping."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        c.post("/api/sim/control", json={"action": "reset", "seed": 42})
        yield c


def step(c, n=1):
    for _ in range(n):
        r = c.post("/api/sim/control", json={"action": "step"})
        assert r.status_code == 200
    return r.json()


def test_health_reports_snapshot_weather(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["noaa"] == "snapshot"


def test_initial_snapshot(client):
    s = client.get("/api/sim/state").json()
    assert s["tick"] == 0 and s["status"] == "paused" and s["seed"] == 42
    assert len(s["esl"]) == 8 and s["kpis"]["waste_reduction_pct"] is None
    assert s["weather"]["source"] == "snapshot"


def test_step_advances_one_tick(client):
    assert step(client) == {"status": "paused", "tick": 1, "speed": 1}
    assert len(client.get("/api/sim/state").json()["chart"]) == 1


def test_rainstorm_queues_and_logs(client):
    step(client, 9)
    r = client.post("/api/sim/events", json={"type": "rainstorm"})
    assert r.json() == {"queued": True, "apply_at_tick": 9}
    step(client)
    s = client.get("/api/sim/state").json()
    agents = {x["agent"] for x in s["logs"] if x["tick"] == 9}
    assert {"SYSTEM", "DEMAND_AGENT", "PROCUREMENT_AGENT", "RAG_KNOWLEDGE_AGENT"} <= agents
    assert s["weather"]["storm_active"] and s["weather"]["traffic_mult"] == 0.78
    assert s["active_events"][0]["type"] == "rainstorm"
    assert all(row["reason"] == "rainstorm" for row in s["po_table"])
    # second storm while one is active is rejected with the error envelope
    r = client.post("/api/sim/events", json={"type": "rainstorm"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "conflict"


def test_validation_error_envelope(client):
    r = client.post("/api/sim/control", json={"action": "explode"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_request"
    r = client.post(
        "/api/sim/events", json={"type": "cold_chain_delay", "payload": {"skus": ["NOPE-01"]}}
    )
    assert r.status_code == 409


def test_formula(client):
    step(client, 30)
    f = client.get("/api/sim/skus/STRW-01/formula").json()
    assert f["elasticity"] == -2.0 and f["elasticity_is_assumed"] is True
    assert any("FoodKeeper" in s for s in f["sources"])
    assert client.get("/api/sim/skus/NOPE/formula").json()["error"]["code"] == "not_found"


def test_replay_reproduces_run(client):
    step(client, 5)
    client.post(
        "/api/sim/events", json={"type": "cold_chain_delay", "payload": {"immediate": True}}
    )
    step(client, 40)
    first = client.get("/api/sim/state").json()
    client.post("/api/sim/control", json={"action": "reset", "replay": True})
    step(client, 45)
    again = client.get("/api/sim/state").json()
    assert again["kpis"] == first["kpis"] and again["chart"] == first["chart"]


def test_finished_run_ignores_play(client):
    step(client, 168)
    assert client.post("/api/sim/control", json={"action": "play"}).json()["status"] == "finished"
    assert step(client)["tick"] == 168
    assert client.post("/api/sim/events", json={"type": "rainstorm"}).status_code == 409


def test_websocket_hello_ticks_and_ping(client):
    with client.websocket_connect("/ws/sim") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["snapshot"]["tick"] == 0
        step(client, 3)
        ticks = []
        while len(ticks) < 3:
            m = ws.receive_json()
            if m["type"] == "tick":
                ticks.append(m)
        assert [m["tick"] for m in ticks] == [1, 2, 3]
        assert len(ticks[0]["delta"]["esl"]) == 8
        assert ticks[0]["delta"]["po_table"] is not None  # first delta carries everything
        ws.send_text("ping")
        while (m := ws.receive_json())["type"] != "pong":
            pass
