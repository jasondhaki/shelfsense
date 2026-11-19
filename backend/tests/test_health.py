from fastapi.testclient import TestClient

from app.main import app


def test_health():
    r = TestClient(app).get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["vision_mode"] in ("cached", "live")


def test_root_ping_for_uptime_monitor():
    client = TestClient(app)
    for path in ("/", "/healthz"):
        r = client.get(path)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert client.head(path).status_code == 200
