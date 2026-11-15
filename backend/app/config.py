from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    app_env: str = "dev"
    cors_origins: str = "http://localhost:5173"
    sim_seed: int = 42
    vision_mode: Literal["cached", "live"] = "cached"
    gemini_api_key: str = ""
    gemini_vision_model: str = ""
    gemini_embed_model: str = ""
    rag_mode: Literal["auto", "vector", "bm25"] = "auto"
    noaa_enabled: bool = True
    noaa_lat: float = 40.7128
    noaa_lon: float = -74.0060
    noaa_user_agent: str = "ShelfSense (contact: your-email@example.com)"
    http_timeout_s: float = 8

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
