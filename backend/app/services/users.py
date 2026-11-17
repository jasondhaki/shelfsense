"""User accounts: storage, password hashing and signed session tokens (stdlib crypto only).

DATABASE_URL set → Postgres (Neon free tier in production). Unset → a local SQLite file, so the
app still runs offline (CLAUDE.md rule 4). Passwords are scrypt-hashed with a per-user salt;
tokens are `base64(payload).hmac` signed with AUTH_SECRET.
"""

import base64
import hashlib
import hmac
import json
import logging
import secrets
import sqlite3
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

TOKEN_TTL_S = 30 * 24 * 3600
SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}
SCHEMA = """CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    store TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DOUBLE PRECISION NOT NULL
)"""
FIELDS = "id, email, name, store, password_hash"


@dataclass
class User:
    id: str
    email: str
    name: str
    store: str
    password_hash: str

    @property
    def session_key(self) -> str:
        return f"u-{self.id}"  # this user's own simulation in Sessions


# --- passwords and tokens -------------------------------------------------------------


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        got = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), **SCRYPT)
    except ValueError:
        return False
    return hmac.compare_digest(got.hex(), digest)


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(user_id: str, secret: str, now: float | None = None) -> str:
    payload = _b64(
        json.dumps({"uid": user_id, "exp": int((now or time.time()) + TOKEN_TTL_S)}).encode()
    )
    sig = _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def read_token(token: str | None, secret: str, now: float | None = None) -> str | None:
    """The user id inside a valid, unexpired token, else None."""
    if not token or token.count(".") != 1:
        return None
    payload, sig = token.split(".")
    want = _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    # bytes: compare_digest raises TypeError on non-ASCII str (a crafted token → 500)
    if not hmac.compare_digest(sig.encode(), want.encode()):
        return None
    try:
        data = json.loads(_unb64(payload))
    except ValueError:
        return None
    if not isinstance(data, dict) or data.get("exp", 0) < (now or time.time()):
        return None
    uid = data.get("uid")
    return uid if isinstance(uid, str) else None


class LoginLimiter:
    """At most `limit` failed logins per email per window — enough to stop password guessing
    on a demo without any extra service. ponytail: in-memory, per instance; move to the DB if
    the API ever runs on more than one instance."""

    MAX_KEYS = 10_000  # bounds memory when someone sprays random emails

    def __init__(self, limit: int = 10, window_s: float = 900) -> None:
        self.limit = limit
        self.window_s = window_s
        self.fails: dict[str, deque[float]] = defaultdict(deque)

    def blocked(self, key: str, now: float | None = None) -> bool:
        q = self.fails.get(key)  # .get: a lookup must not create an entry
        if not q:
            return False
        t = now or time.time()
        while q and q[0] < t - self.window_s:
            q.popleft()
        return len(q) >= self.limit

    def fail(self, key: str, now: float | None = None) -> None:
        t = now or time.time()
        if len(self.fails) >= self.MAX_KEYS and key not in self.fails:
            cutoff = t - self.window_s
            for k in [k for k, q in self.fails.items() if not q or q[-1] < cutoff]:
                del self.fails[k]
        self.fails[key].append(t)

    def clear(self, key: str) -> None:
        self.fails.pop(key, None)


# --- storage ----------------------------------------------------------------------------


class EmailTaken(Exception):
    pass


class UserStore:
    def __init__(self, database_url: str, sqlite_path: Path) -> None:
        self.pg = bool(database_url)
        self.database_url = database_url
        self.sqlite_path = sqlite_path
        if not self.pg:
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._exec(SCHEMA)

    @property
    def backend(self) -> str:
        return "postgres" if self.pg else "sqlite"

    def _exec(self, sql: str, args: tuple = (), fetch: bool = False) -> list[tuple]:
        if self.pg:
            import psycopg  # only needed when DATABASE_URL is set

            with psycopg.connect(self.database_url, connect_timeout=15) as conn:
                cur = conn.execute(sql.replace("?", "%s"), args)
                return cur.fetchall() if fetch else []
        with sqlite3.connect(self.sqlite_path) as conn:
            cur = conn.execute(sql, args)
            return cur.fetchall() if fetch else []

    def _one(self, where: str, arg: str) -> User | None:
        rows = self._exec(f"SELECT {FIELDS} FROM users WHERE {where} = ?", (arg,), fetch=True)
        return User(*rows[0]) if rows else None

    def by_email(self, email: str) -> User | None:
        return self._one("email", email)

    def by_id(self, user_id: str) -> User | None:
        return self._one("id", user_id)

    def create(self, email: str, name: str, store: str, password: str) -> User:
        if self.by_email(email):
            raise EmailTaken(email)
        u = User(uuid.uuid4().hex, email, name, store, hash_password(password))
        try:
            self._exec(
                f"INSERT INTO users ({FIELDS}, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (u.id, u.email, u.name, u.store, u.password_hash, time.time()),
            )
        except Exception as e:  # a racing signup with the same email hits the UNIQUE index
            if "unique" in str(e).lower():
                raise EmailTaken(email) from None
            raise
        return u

    def update_profile(self, user_id: str, name: str, store: str) -> None:
        self._exec("UPDATE users SET name = ?, store = ? WHERE id = ?", (name, store, user_id))
