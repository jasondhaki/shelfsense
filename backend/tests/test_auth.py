import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.users import LoginLimiter, make_token, read_token


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def signup(c, email, name="Ayesha", store="Bay 7", password="correct horse"):
    return c.post(
        "/api/auth/signup",
        json={"email": email, "password": password, "name": name, "store": store},
    )


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_signup_login_me_and_profile(client):
    r = signup(client, "Ayesha@Example.com ")
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "ayesha@example.com" and body["user"]["name"] == "Ayesha"
    assert "password" not in str(body["user"])

    assert signup(client, "ayesha@example.com").status_code == 409
    bad = client.post(
        "/api/auth/login", json={"email": "ayesha@example.com", "password": "wrong pass"}
    )
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "unauthorized"

    tok = client.post(
        "/api/auth/login", json={"email": "AYESHA@example.com", "password": "correct horse"}
    ).json()["token"]
    assert client.get("/api/auth/me", headers=auth(tok)).json()["store"] == "Bay 7"
    r = client.patch("/api/auth/me", headers=auth(tok), json={"name": " Rafi ", "store": "Uttara"})
    assert r.status_code == 200 and r.json()["name"] == "Rafi"
    assert client.get("/api/auth/me", headers=auth(tok)).json()["store"] == "Uttara"


def test_validation_and_unauthenticated(client):
    assert signup(client, "not-an-email").status_code == 422
    assert signup(client, "short@example.com", password="1234567").status_code == 422
    assert signup(client, "blank@example.com", name="   ").status_code == 422
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=auth("forged.token")).status_code == 401


def test_each_user_has_their_own_simulation(client):
    a = signup(client, "a@example.com").json()["token"]
    b = signup(client, "b@example.com").json()["token"]
    client.post("/api/sim/control", headers=auth(a), json={"action": "step"})
    assert client.get("/api/sim/state", headers=auth(a)).json()["tick"] == 1
    assert client.get("/api/sim/state", headers=auth(b)).json()["tick"] == 0
    # a guest can't reach a user's run by sending its reserved session key
    uid = client.get("/api/auth/me", headers=auth(a)).json()["id"]
    probe = client.get("/api/sim/state", headers={"X-Session-Id": f"u-{uid}"}).json()
    assert probe["tick"] == client.get("/api/sim/state").json()["tick"]  # the shared run


def test_websocket_uses_the_token(client):
    tok = signup(client, "ws@example.com").json()["token"]
    client.post("/api/sim/control", headers=auth(tok), json={"action": "step"})
    client.post("/api/sim/control", headers=auth(tok), json={"action": "step"})
    with client.websocket_connect(f"/ws/sim?token={tok}") as ws:
        assert ws.receive_json()["snapshot"]["tick"] == 2


def test_token_signing_and_expiry():
    t = make_token("u1", "s", now=1000)
    assert read_token(t, "s", now=1001) == "u1"
    assert read_token(t, "other", now=1001) is None
    assert read_token(t, "s", now=1000 + 31 * 24 * 3600) is None
    payload, sig = t.split(".")
    assert read_token(payload[:-1] + "A." + sig, "s", now=1001) is None


def test_login_limiter():
    lim = LoginLimiter(limit=3, window_s=60)
    now = time.time()
    for _ in range(3):
        lim.fail("x", now)
    assert lim.blocked("x", now) and not lim.blocked("x", now + 61)


def test_hostile_tokens_never_crash(client):
    assert read_token("a.é", "s") is None  # non-ASCII signature used to raise TypeError
    with client.websocket_connect("/ws/sim?session=hostile-token-1&token=a.%C3%A9") as ws:
        assert ws.receive_json()["type"] == "hello"  # falls back to the guest session


def test_limiter_lookups_do_not_grow_memory():
    lim = LoginLimiter(limit=3, window_s=60)
    for i in range(100):
        lim.blocked(f"nobody{i}@example.com")
    assert not lim.fails
