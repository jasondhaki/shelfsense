import logging
import re
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.agents.rag_agent import all_queries
from app.api import auth, routes, ws
from app.config import get_settings
from app.controller import Sessions, SimController
from app.rag.retriever import Retriever
from app.services import gemini
from app.services.noaa import NoaaService
from app.services.open_meteo import OpenMeteoService
from app.services.users import UserStore

log = logging.getLogger(__name__)

VERSION = "0.3.0"


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


MAX_BODY_BYTES = 6 * 1024 * 1024  # 5 MB image + multipart overhead; JSON bodies are tiny


class BodyLimit:
    """Reject request bodies over MAX_BODY_BYTES while streaming (Content-Length can be absent
    or lie). Starlette spools uploads to disk with no size cap, and JSON is read into memory."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        seen = 0

        async def limited():
            nonlocal seen
            msg = await receive()
            seen += len(msg.get("body", b""))
            if seen > MAX_BODY_BYTES:
                raise HTTPException(413, "Request body is too large.")
            return msg

        declared = dict(scope["headers"]).get(b"content-length", b"0")
        if declared.isdigit() and int(declared) > MAX_BODY_BYTES:
            return await _error(413, "too_large", "Request body is too large.")(
                scope, receive, send
            )
        await self.app(scope, limited, send)


class _RedactTokens(logging.Filter):
    """uvicorn logs WebSocket/request paths with their query string: keep ?token= out of logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(
                TOKEN_RE.sub(r"\1***", a) if isinstance(a, str) else a for a in record.args
            )
        return True


TOKEN_RE = re.compile(r"([?&]token=)[^&\s\"]+")
for _name in ("uvicorn.access", "uvicorn.error"):
    logging.getLogger(_name).addFilter(_RedactTokens())


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        noaa = (
            OpenMeteoService(settings)
            if settings.weather_provider == "open_meteo"
            else NoaaService(settings)
        )
        await noaa.refresh()
        retriever = Retriever(
            settings.rag_mode,
            vector_ready=bool(settings.gemini_api_key and settings.gemini_embed_model),
            embed_model=settings.gemini_embed_model,
        )
        sessions = Sessions(lambda: SimController(settings.sim_seed, noaa, retriever))
        shared = sessions.get(None)
        # vector mode: embed every templated query once now, so ticks never wait on the network
        await retriever.warm(
            all_queries(shared.state.config), lambda qs: gemini.embed(qs, settings)
        )
        app.state.sessions = sessions
        app.state.auth_secret = settings.auth_secret or secrets.token_urlsafe(32)
        if not settings.auth_secret:
            log.warning("AUTH_SECRET not set: sign-ins last until this process restarts")
        try:
            app.state.users = UserStore(settings.database_url, settings.users_db_path)
        except Exception as e:  # accounts down must not take the demo down (rule 4)
            log.error("User store unavailable, guests only: %s", e)
            app.state.users = None
        app.state.retriever = retriever
        app.state.noaa = noaa
        yield
        await sessions.pause_all()

    app = FastAPI(title="ShelfSense", version=VERSION, lifespan=lifespan)
    app.add_middleware(BodyLimit)  # added first = inside CORS, so a 413 still carries CORS headers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        code = {
            401: "unauthorized",
            404: "not_found",
            409: "conflict",
            413: "too_large",
            422: "invalid_request",
            429: "rate_limited",
            503: "unavailable",
        }.get(exc.status_code, "http_error")
        return _error(exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(x) for x in first.get("loc", []))
        return _error(422, "invalid_request", f"{loc}: {first.get('msg', 'invalid request')}")

    @app.get("/api/health")
    def health(request: Request) -> dict:
        r = getattr(request.app.state, "retriever", None)
        n = getattr(request.app.state, "noaa", None)
        rag = r.mode if r else "bm25"
        return {
            "status": "ok",
            "version": VERSION,
            "vision_mode": settings.vision_mode,
            "rag_mode": rag,
            "noaa": n.source if n else "snapshot",
            "weather_provider": settings.weather_provider,
            "accounts": (u.backend if (u := getattr(request.app.state, "users", None)) else "off"),
        }

    app.include_router(auth.router)
    app.include_router(routes.router)
    app.include_router(ws.router)
    return app


app = create_app()
