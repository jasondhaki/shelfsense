"""Accounts: sign up, log in, read and edit your profile. Each signed-in user gets their own
simulation (Sessions key `u-<id>`); guests keep the per-tab X-Session-Id simulation."""

import re

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from starlette.requests import HTTPConnection

from app.services.users import (
    DUMMY_HASH,
    EmailTaken,
    LoginLimiter,
    User,
    make_token,
    read_claims,
    verify_password,
)

router = APIRouter(prefix="/api/auth")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
limiter = LoginLimiter()
# signups cost a 16 MB scrypt + a DB row: cap per client and overall per instance
signup_per_client = LoginLimiter(limit=10, window_s=3600)
signup_global = LoginLimiter(limit=200, window_s=3600)


def _client(request: Request) -> str:
    """The caller's IP. Render sits behind Cloudflare, which overwrites these two headers at
    the edge; X-Forwarded-For is not used because Render appends to whatever the client sent."""
    h = request.headers
    ip = h.get("true-client-ip") or h.get("cf-connecting-ip")
    return ip.strip() if ip else (request.client.host if request.client else "?")


def _email(v: str) -> str:
    v = v.strip().lower()
    if not EMAIL.match(v) or len(v) > 254:
        raise ValueError("enter a valid email address")
    return v


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=40)
    store: str = Field(min_length=1, max_length=40)

    _e = field_validator("email")(_email)

    @field_validator("name", "store")
    @classmethod
    def _strip(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("can't be blank")
        return v.strip()


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    _e = field_validator("email")(_email)


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    store: str = Field(min_length=1, max_length=40)

    @field_validator("name", "store")
    @classmethod
    def _strip(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("can't be blank")
        return v.strip()


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    store: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


def _out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, name=u.name, store=u.store)


def _store(request: Request):
    s = getattr(request.app.state, "users", None)
    if s is None:
        raise HTTPException(503, "Accounts are unavailable right now. Continue as a guest.")
    return s


def bearer(request: HTTPConnection) -> str | None:
    h = request.headers.get("authorization", "")
    return h[7:] if h.lower().startswith("bearer ") else None


def user_id(request: HTTPConnection, token: str | None = None) -> str | None:
    """The signed-in user's id from a valid token that wasn't revoked by a sign-out
    (cached check: a DB read at most once per user per REVOKE_CACHE_S)."""
    claims = read_claims(token or bearer(request), request.app.state.auth_secret)
    if claims is None:
        return None
    users = getattr(request.app.state, "users", None)
    if users is not None and users.revoked(claims["uid"], claims["iat"]):
        return None
    return claims["uid"]


def _me(request: Request) -> User:
    uid = user_id(request)
    u = _store(request).by_id(uid) if uid else None
    if u is None:
        raise HTTPException(401, "Sign in to continue.")
    return u


@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup(body: SignupRequest, request: Request) -> AuthResponse:
    who = _client(request)
    if signup_per_client.blocked(who) or signup_global.blocked("all"):
        raise HTTPException(429, "Too many sign-ups right now. Try again later.")
    signup_per_client.fail(who)
    signup_global.fail("all")
    try:
        u = _store(request).create(body.email, body.name, body.store, body.password)
    except EmailTaken:
        msg = "An account with this email already exists. Sign in instead."
        raise HTTPException(409, msg) from None
    return AuthResponse(token=make_token(u.id, request.app.state.auth_secret), user=_out(u))


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, request: Request) -> AuthResponse:
    if limiter.blocked(body.email):
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    u = _store(request).by_email(body.email)
    # same scrypt cost whether or not the email exists, so timing doesn't reveal accounts
    if not verify_password(body.password, u.password_hash if u else DUMMY_HASH) or u is None:
        limiter.fail(body.email)
        raise HTTPException(401, "Email or password is incorrect.")
    limiter.clear(body.email)
    return AuthResponse(token=make_token(u.id, request.app.state.auth_secret), user=_out(u))


@router.get("/me", response_model=UserOut)
def me(request: Request) -> UserOut:
    return _out(_me(request))


@router.post("/logout", status_code=204)
def logout(request: Request) -> Response:
    """Sign out on every device: all tokens issued so far stop working."""
    u = _me(request)
    _store(request).sign_out_everywhere(u.id)
    return Response(status_code=204)


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfileUpdate, request: Request) -> UserOut:
    u = _me(request)
    _store(request).update_profile(u.id, body.name, body.store)
    u.name, u.store = body.name, body.store
    return _out(u)
