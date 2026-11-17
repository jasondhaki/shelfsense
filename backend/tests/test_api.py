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
    for bad in ({"skus": 5}, {"skus": None, "junk": "x"}, {"skus": [["x"]]}, {"immediate": "x"}):
        r = client.post("/api/sim/events", json={"type": "cold_chain_delay", "payload": bad})
        assert r.status_code == 422, bad  # used to be a 500, or junk stored + broadcast


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


def test_architecture_reports_offline_status(client):
    a = client.get("/api/meta/architecture").json()
    nodes = {n["id"]: n for n in a["nodes"]}
    assert nodes["vision"]["status"] == "fallback" and nodes["rag"]["status"] == "fallback"
    assert nodes["noaa"]["status"] == "fallback" and nodes["pricing"]["agent"] == "PRICING_AGENT"
    ids = set(nodes)
    assert all(e["source"] in ids and e["target"] in ids for e in a["edges"])


def test_demo_scenario_reset_runs_scripted_events(client):
    r = client.post("/api/sim/control", json={"action": "reset", "scenario": "demo"})
    assert r.json()["tick"] == 0
    step(client, 87)
    types = [e["type"] for e in client.get("/api/sim/state").json()["active_events"]]
    logs = client.get("/api/sim/state").json()["logs"]
    assert any(x["agent"] == "VISION_AGENT" and "frame3 (scripted)" in x["message"] for x in logs)
    assert isinstance(types, list)


def test_sessions_are_isolated(client):
    a = {"X-Session-Id": "tab-aaaaaaaa"}
    b = {"X-Session-Id": "tab-bbbbbbbb"}
    for _ in range(3):
        client.post("/api/sim/control", json={"action": "step"}, headers=a)
    assert client.get("/api/sim/state", headers=a).json()["tick"] == 3
    assert client.get("/api/sim/state", headers=b).json()["tick"] == 0
    # malformed ids share the default simulation instead of creating new ones
    bad = {"X-Session-Id": "x"}
    assert (
        client.get("/api/sim/state", headers=bad).json()["tick"]
        == client.get("/api/sim/state").json()["tick"]
    )
    with client.websocket_connect("/ws/sim?session=tab-aaaaaaaa") as ws:
        assert ws.receive_json()["snapshot"]["tick"] == 3


def test_session_cap_evicts_least_recent():
    from app.controller import Sessions

    made = []

    class Fake:
        playing = True
        subscribers: set = set()

    s = Sessions(lambda _key: made.append(Fake()) or made[-1], cap=2)
    first = s.get("session-0001")
    s.get("session-0002")
    s.get("session-0003")
    assert len(s.items) == 2 and "session-0001" not in s.items and first.playing is False


def test_report_csv(client):
    step(client, 5)
    r = client.get("/api/sim/report.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("tick,sim_time,waste_kg_baseline")
    assert lines[1].startswith("0,D1 00:00") and len([x for x in lines if x[:1].isdigit()]) == 5
    assert any(x.startswith("waste_reduction_pct") for x in lines)


def test_baseline_store_labels(client):
    step(client, 2)
    s = client.get("/api/sim/state").json()
    a = {e["sku_id"]: e for e in s["esl_a"]}
    assert len(a) == 8
    assert all(e["rsl_hours"] == max(e["printed_remaining_hours"], 0) for e in a.values())


def test_ui_fields_for_freshness_and_sparklines(client):
    step(client, 3)
    s = client.get("/api/sim/state").json()
    for e in s["esl"] + s["esl_a"]:
        assert e["shelf_life_hours"] > 0 and e["rsl_hours"] <= e["shelf_life_hours"] + 1e-6
    last = s["chart"][-1]
    assert last["co2e_avoided_kg"] == pytest.approx(s["kpis"]["co2e_avoided_kg"])
    assert last["net_margin_recovered_usd"] == pytest.approx(s["kpis"]["net_margin_recovered_usd"])


def test_oversized_bodies_rejected(client):
    from app.main import MAX_BODY_BYTES

    big = b"\xff\xd8\xff" + b"0" * (MAX_BODY_BYTES + 10)
    r = client.post("/api/vision/scan", files={"file": ("x.jpg", big, "image/jpeg")})
    assert r.status_code == 413

    def chunks():  # no Content-Length: the streaming check must still stop it
        for _ in range(7):
            yield b"0" * (1024 * 1024)

    r = client.post(
        "/api/sim/events", content=chunks(), headers={"content-type": "application/json"}
    )
    assert r.status_code == 413


def test_tokens_redacted_from_server_logs():
    import logging

    from app.main import _RedactTokens

    rec = logging.LogRecord(
        "uvicorn.error",
        20,
        "",
        0,
        '%s - "WebSocket %s"',
        ("ip", "/ws/sim?session=x&token=abc.def"),
        None,
    )
    _RedactTokens().filter(rec)
    assert "abc.def" not in rec.getMessage() and "token=***" in rec.getMessage()


def test_guest_churn_cannot_evict_signed_in_or_watched_runs():
    from app.controller import Sessions

    class Fake:
        def __init__(self, _key=None):
            self.subscribers = set()
            self.playing = True

    s = Sessions(Fake, cap=3)
    user = s.get("u-" + "a" * 32)
    watched = s.get("guest-watched-1")
    watched.subscribers.add(object())
    for i in range(20):
        s.get(f"guest-churn-{i:04d}")
    assert s.items["u-" + "a" * 32] is user and user.playing
    assert s.items["guest-watched-1"] is watched
    assert sum(not k.startswith("u-") for k in s.items) == 3
