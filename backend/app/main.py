from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.agents.rag_agent import all_queries
from app.api import routes, ws
from app.config import get_settings
from app.controller import SimController
from app.rag.retriever import Retriever
from app.services import gemini
from app.services.noaa import NoaaService

VERSION = "0.3.0"


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        noaa = NoaaService(settings)
        await noaa.refresh()
        retriever = Retriever(
            settings.rag_mode,
            vector_ready=bool(settings.gemini_api_key and settings.gemini_embed_model),
            embed_model=settings.gemini_embed_model,
        )
        ctl = SimController(settings.sim_seed, noaa, retriever)
        # vector mode: embed every templated query once now, so ticks never wait on the network
        await retriever.warm(all_queries(ctl.state.config), lambda qs: gemini.embed(qs, settings))
        app.state.controller = ctl
        yield
        await app.state.controller.control("pause")

    app = FastAPI(title="ShelfSense", version=VERSION, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        code = {404: "not_found", 409: "conflict", 413: "too_large", 422: "invalid_request"}.get(
            exc.status_code, "http_error"
        )
        return _error(exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(x) for x in first.get("loc", []))
        return _error(422, "invalid_request", f"{loc}: {first.get('msg', 'invalid request')}")

    @app.get("/api/health")
    def health(request: Request) -> dict:
        ctl = getattr(request.app.state, "controller", None)
        rag = ctl.retriever.mode if ctl else "bm25"
        return {
            "status": "ok",
            "version": VERSION,
            "vision_mode": settings.vision_mode,
            "rag_mode": rag,
            "noaa": ctl.noaa.source if ctl else "snapshot",
        }

    app.include_router(routes.router)
    app.include_router(ws.router)
    return app


app = create_app()
