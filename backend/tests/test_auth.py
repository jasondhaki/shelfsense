import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.users import LoginLimiter, make_token, read_token
from tests.conftest import SENT


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def signup(c, email, name="Ayesha", store="Bay 7", password="correct horse"):
    return c.post(
        "/api/auth/signup",
        json={"email": email, "password": password, "name": name, "store": store},
    )


def verify(c, email, code=None, password="correct horse"):
    code = code or SENT[email.strip().lower()]
    return c.post("/api/auth/verify", json={"email": email, "password": password, "code": code})


def register(c, email, **kw):
    """Sign up + verify: the {token, user} a new account ends with."""
    assert signup(c, email, **kw).status_code == 202
    r = verify(c, email, password=kw.get("password", "correct horse"))
    assert r.status_code == 200, r.text
    return r


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_signup_login_me_and_profile(client):
    r = register(client, "Ayesha@Example.com ")
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
    a = register(client, "a@example.com").json()["token"]
    b = register(client, "b@example.com").json()["token"]
    client.post("/api/sim/control", headers=auth(a), json={"action": "step"})
    assert client.get("/api/sim/state", headers=auth(a)).json()["tick"] == 1
    assert client.get("/api/sim/state", headers=auth(b)).json()["tick"] == 0
    # a guest can't reach a user's run by sending its reserved session key
    uid = client.get("/api/auth/me", headers=auth(a)).json()["id"]
    probe = client.get("/api/sim/state", headers={"X-Session-Id": f"u-{uid}"}).json()
    assert probe["tick"] == client.get("/api/sim/state").json()["tick"]  # the shared run


def test_websocket_uses_the_token(client):
    tok = register(client, "ws@example.com").json()["token"]
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


def test_logout_revokes_every_token(client):
    r = register(client, "logout@example.com")
    old = r.json()["token"]
    other_device = client.post(
        "/api/auth/login", json={"email": "logout@example.com", "password": "correct horse"}
    ).json()["token"]
    auth = {"Authorization": f"Bearer {old}"}
    assert client.post("/api/auth/logout", headers=auth).status_code == 204
    for t in (old, other_device):  # both devices are signed out
        assert (
            client.get("/api/auth/me", headers={"Authorization": f"Bearer {t}"}).status_code == 401
        )
    fresh = client.post(
        "/api/auth/login", json={"email": "logout@example.com", "password": "correct horse"}
    ).json()["token"]  # signing back in right away works
    assert (
        client.get("/api/auth/me", headers={"Authorization": f"Bearer {fresh}"}).status_code == 200
    )
    assert client.post("/api/auth/logout").status_code == 401


def test_signup_limit_keys_on_edge_ip_not_forwarded_for(client):
    from app.api import auth

    auth.signup_per_client.fails.clear()
    for i in range(10):  # a rotating X-Forwarded-For must not reset the per-client count
        h = {"X-Forwarded-For": f"10.0.0.{i}", "CF-Connecting-IP": "203.0.113.9"}
        client.post(
            "/api/auth/signup",
            json={
                "email": f"rl{i}@example.com",
                "password": "correct horse",
                "name": "A",
                "store": "B",
            },
            headers=h,
        )
    h = {"X-Forwarded-For": "10.9.9.9", "CF-Connecting-IP": "203.0.113.9"}
    r = client.post(
        "/api/auth/signup",
        json={
            "email": "rl-last@example.com",
            "password": "correct horse",
            "name": "A",
            "store": "B",
        },
        headers=h,
    )
    assert r.status_code == 429
    auth.signup_per_client.fails.clear()


def test_signup_needs_the_emailed_code(client):
    email = "verify@example.com"
    r = signup(client, email)
    assert r.status_code == 202 and r.json() == {"verify": True, "email": email}
    assert "token" not in r.text
    pw = {"email": email, "password": "correct horse"}
    r = client.post("/api/auth/login", json=pw)  # right password, not verified yet
    assert r.status_code == 403 and r.json()["error"]["code"] == "email_unverified"
    assert "under a minute ago" in r.json()["error"]["message"]  # no second email so soon
    good = SENT[email]
    wrong = f"{(int(good) + 1) % 10**6:06d}"
    assert verify(client, email, wrong).status_code == 422
    assert verify(client, email, good, password="wrong pass").status_code == 401
    assert verify(client, email, "12ab56").status_code == 422  # not 6 digits
    tok = verify(client, email, good).json()["token"]
    assert client.get("/api/auth/me", headers=auth(tok)).json()["email"] == email
    assert client.post("/api/auth/login", json=pw).status_code == 200


def test_code_dies_after_too_many_wrong_guesses(client):
    email = "guess@example.com"
    signup(client, email)
    good = SENT[email]
    for i in range(5):
        verify(client, email, f"{(int(good) + 1 + i) % 10**6:06d}")
    assert verify(client, email, good).status_code == 422


def test_unverified_address_cannot_be_squatted(client):
    email = "owner@example.com"
    signup(client, email, password="attacker pw 1")  # someone else gets there first
    signup(client, email, password="owner pw 123")  # the real owner signs up too
    code = SENT[email]  # both codes land in the owner's inbox
    assert verify(client, email, code, password="attacker pw 1").status_code == 401
    assert verify(client, email, code, password="owner pw 123").status_code == 200
    assert signup(client, email).status_code == 409  # verified now: taken


def test_password_reset(client):
    email = "forgot@example.com"
    old = register(client, email).json()["token"]
    SENT.pop(email, None)
    r = client.post("/api/auth/forgot", json={"email": email})
    same = client.post("/api/auth/forgot", json={"email": "nobody-here@example.com"})
    assert r.status_code == same.status_code == 202 and r.json() == same.json()  # no enumeration
    assert "nobody-here@example.com" not in SENT
    code = SENT[email]
    body = {"email": email, "code": code, "password": "brand new pw"}
    bad = {**body, "code": f"{(int(code) + 1) % 10**6:06d}"}
    assert client.post("/api/auth/reset", json=bad).status_code == 422
    tok = client.post("/api/auth/reset", json=body).json()["token"]
    assert client.get("/api/auth/me", headers=auth(tok)).status_code == 200
    assert client.get("/api/auth/me", headers=auth(old)).status_code == 401  # other devices out
    login = {"email": email, "password": "correct horse"}
    assert client.post("/api/auth/login", json=login).status_code == 401
    login["password"] = "brand new pw"
    assert client.post("/api/auth/login", json=login).status_code == 200
    assert client.post("/api/auth/reset", json=body).status_code == 422  # code is single-use
