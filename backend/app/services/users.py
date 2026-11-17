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
SIMS = """CREATE TABLE IF NOT EXISTS sims (
    user_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL
)"""
# columns added after launch. SQLite has no ADD COLUMN IF NOT EXISTS, so each is tried and a
# "duplicate"/"already exists" error ignored. Accounts made before verification count as verified.
MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN sessions_after DOUBLE PRECISION NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1",
    "ALTER TABLE users ADD COLUMN code_hash TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE users ADD COLUMN code_sent_at DOUBLE PRECISION NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN code_attempts INTEGER NOT NULL DEFAULT 0",
]
FIELDS = "id, email, name, store, password_hash, email_verified"
REVOKE_CACHE_S = 600  # sign-out updates the cache directly, so this only bounds DB reads
CODE_TTL_S = 15 * 60
CODE_RESEND_S = 60  # minimum gap between two codes to the same address
CODE_MAX_ATTEMPTS = 5  # wrong guesses before the code is void and a new one is needed


@dataclass
class User:
    id: str
    email: str
    name: str
    store: str
    password_hash: str
    verified: bool = True

    def __post_init__(self) -> None:
        self.verified = bool(self.verified)  # SQLite/Postgres INTEGER → bool

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


# verified when the email is unknown, so a failed login takes the same time either way
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def _code_hash(user_id: str, code: str) -> str:
    # keyed by account so equal codes for two users differ; a 6-digit code is guessable offline,
    # which is why it also expires and allows CODE_MAX_ATTEMPTS tries
    return hashlib.sha256(f"{user_id}:{code}".encode()).hexdigest()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(user_id: str, secret: str, now: float | None = None) -> str:
    t = now or time.time()
    claims = {"uid": user_id, "iat": t, "exp": int(t + TOKEN_TTL_S)}
    payload = _b64(json.dumps(claims).encode())
    sig = _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def read_token(token: str | None, secret: str, now: float | None = None) -> str | None:
    """The user id inside a valid, unexpired token, else None."""
    claims = read_claims(token, secret, now)
    return claims["uid"] if claims else None


def read_claims(token: str | None, secret: str, now: float | None = None) -> dict | None:
    """{uid, iat} from a valid, unexpired token, else None. Tokens from before sign-out
    existed carry no iat: they read as 0, so a later sign-out still revokes them."""
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
    uid, iat = data.get("uid"), data.get("iat", 0)
    if not isinstance(uid, str) or not isinstance(iat, (int, float)):
        return None
    return {"uid": uid, "iat": float(iat)}


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
        self._exec(SIMS)
        for sql in MIGRATIONS:
            try:
                self._exec(sql)
            except Exception as e:  # column already there (migrated on an earlier start)
                if "duplicate" not in str(e).lower() and "already exists" not in str(e).lower():
                    raise
        self._after: dict[str, tuple[float, float]] = {}  # uid -> (sessions_after, read at)

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
        """A new, unverified account. Signing up again before verifying replaces the details
        (so nobody can squat an address they can't read); a verified address is taken."""
        old = self.by_email(email)
        if old and old.verified:
            raise EmailTaken(email)
        h = hash_password(password)
        if old:
            self._exec(
                "UPDATE users SET name = ?, store = ?, password_hash = ? WHERE id = ?",
                (name, store, h, old.id),
            )
            return User(old.id, email, name, store, h, False)
        u = User(uuid.uuid4().hex, email, name, store, h, False)
        try:
            self._exec(
                f"INSERT INTO users ({FIELDS}, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (u.id, u.email, u.name, u.store, u.password_hash, 0, time.time()),
            )
        except Exception as e:  # a racing signup with the same email hits the UNIQUE index
            if "unique" in str(e).lower():
                raise EmailTaken(email) from None
            raise
        return u

    # --- email verification codes ------------------------------------------------------

    def new_code(self, user_id: str, now: float | None = None) -> str | None:
        """A fresh 6-digit code (the old one stops working), or None if one went out less
        than CODE_RESEND_S ago. Only a hash is stored."""
        t = now or time.time()
        rows = self._exec("SELECT code_sent_at FROM users WHERE id = ?", (user_id,), fetch=True)
        if rows and t - float(rows[0][0]) < CODE_RESEND_S:
            return None
        code = f"{secrets.randbelow(10**6):06d}"
        self._exec(
            "UPDATE users SET code_hash = ?, code_sent_at = ?, code_attempts = 0 WHERE id = ?",
            (_code_hash(user_id, code), t, user_id),
        )
        return code

    def check_code(self, user_id: str, code: str, now: float | None = None) -> bool:
        """True (and the account becomes verified) if `code` is the live code."""
        rows = self._exec(
            "SELECT code_hash, code_sent_at, code_attempts FROM users WHERE id = ?",
            (user_id,),
            fetch=True,
        )
        if not rows:
            return False
        stored, sent_at, attempts = rows[0]
        live = (
            stored and attempts < CODE_MAX_ATTEMPTS and (now or time.time()) - sent_at < CODE_TTL_S
        )
        if live and hmac.compare_digest(stored, _code_hash(user_id, code)):
            self._exec(
                # used up: void it, and lift the resend cooldown so a new code can follow at once
                "UPDATE users SET email_verified = 1, code_hash = '', code_sent_at = 0 "
                "WHERE id = ?",
                (user_id,),
            )
            return True
        self._exec("UPDATE users SET code_attempts = code_attempts + 1 WHERE id = ?", (user_id,))
        return False

    # --- saved simulations ---------------------------------------------------------------

    def save_sim(self, user_id: str, data: dict) -> None:
        self._exec(
            "INSERT INTO sims (user_id, data, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id) DO UPDATE SET data = excluded.data, "
            "updated_at = excluded.updated_at",
            (user_id, json.dumps(data), time.time()),
        )

    def load_sim(self, user_id: str) -> dict | None:
        rows = self._exec("SELECT data FROM sims WHERE user_id = ?", (user_id,), fetch=True)
        return json.loads(rows[0][0]) if rows else None

    def set_password(self, user_id: str, password: str) -> None:
        h = hash_password(password)
        self._exec("UPDATE users SET password_hash = ? WHERE id = ?", (h, user_id))

    def update_profile(self, user_id: str, name: str, store: str) -> None:
        self._exec("UPDATE users SET name = ?, store = ? WHERE id = ?", (name, store, user_id))

    # --- sign-out (token revocation) --------------------------------------------------

    def sign_out_everywhere(self, user_id: str, now: float | None = None) -> None:
        """Every token issued before now stops working, on every device."""
        t = now or time.time()
        self._exec("UPDATE users SET sessions_after = ? WHERE id = ?", (t, user_id))
        self._after[user_id] = (t, time.monotonic())

    def revoked(self, user_id: str, issued_at: float) -> bool:
        """True when the token was issued before this user's last sign-out. Cached so routing
        a request rarely touches the DB. ponytail: per-process cache; with several instances
        a sign-out reaches the others within REVOKE_CACHE_S."""
        hit = self._after.get(user_id)
        if hit is None or time.monotonic() - hit[1] > REVOKE_CACHE_S:
            try:
                rows = self._exec(
                    "SELECT sessions_after FROM users WHERE id = ?", (user_id,), fetch=True
                )
            except Exception as e:  # DB blip: keep the last known value rather than sign out
                log.warning("sign-out check failed: %s", e)
                return bool(hit and issued_at < hit[0])
            if not rows:
                return True  # account no longer exists
            hit = self._after[user_id] = (float(rows[0][0]), time.monotonic())
        return issued_at < hit[0]
