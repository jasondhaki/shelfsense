from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

VERSION = "0.1.0"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="ShelfSense", version=VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict:
        rag = settings.rag_mode
        if rag == "auto":
            rag = "vector" if settings.gemini_api_key else "bm25"
        return {
            "status": "ok",
            "version": VERSION,
            "vision_mode": settings.vision_mode,
            "rag_mode": rag,
            "noaa": "snapshot",  # live NOAA service lands in Phase 3
        }

    return app


app = create_app()
