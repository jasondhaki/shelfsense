"""Signed-in runs survive a restart; guest runs don't. Each `with TestClient(app)` runs the
lifespan, so the second one starts with empty memory, exactly like a redeploy."""

from fastapi.testclient import TestClient

from app.main import app
from tests.test_auth import auth, register


def test_signed_in_week_survives_a_restart():
    guest = {"X-Session-Id": "persist-guest-1"}
    with TestClient(app) as c:
        tok = register(c, "keep@example.com").json()["token"]
        h = auth(tok)
        for _ in range(5):
            c.post("/api/sim/control", headers=h, json={"action": "step"})
        assert c.post("/api/sim/events", headers=h, json={"type": "rainstorm"}).status_code == 200
        for _ in range(3):
            c.post("/api/sim/control", headers=h, json={"action": "step"})
        c.post("/api/sim/control", headers=guest, json={"action": "step"})
        before = c.get("/api/sim/state", headers=h).json()

    with TestClient(app) as c:
        after = c.get("/api/sim/state", headers=auth(tok)).json()
        assert c.get("/api/sim/state", headers=guest).json()["tick"] == 0  # guests: memory only

    assert after["tick"] == before["tick"] == 8
    for k in ("kpis", "esl", "po_table", "chart", "active_events", "logs"):
        assert after[k] == before[k], k
