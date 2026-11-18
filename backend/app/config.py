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
    # plain-language explanations (AI_PIPELINE §3): none = template text only
    llm_provider: Literal["none", "gemini", "ollama", "openai_compat"] = "none"
    gemini_text_model: str = ""  # empty → GEMINI_VISION_MODEL
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = ""  # a local open-weight model, e.g. qwen2.5:3b
    # any OpenAI-compatible local server: llama.cpp llama-server, LM Studio, vLLM
    openai_compat_url: str = "http://localhost:8080/v1"
    openai_compat_model: str = ""
    llm_timeout_s: float = 30
    weather_provider: Literal["noaa", "open_meteo"] = "noaa"  # header widget source
    noaa_enabled: bool = True  # live weather on/off (either provider)
    open_meteo_lat: float = 23.8103  # Dhaka
    open_meteo_lon: float = 90.4125
    open_meteo_location: str = "Dhaka, BD"
    noaa_lat: float = 40.7128
    noaa_lon: float = -74.0060
    noaa_user_agent: str = "ShelfSense (contact: your-email@example.com)"
    http_timeout_s: float = 8
    vision_timeout_s: float = 60  # multimodal + reasoning models are slow; one try, no retry
    database_url: str = ""  # Postgres for accounts (Neon free); empty → local SQLite file
    users_db_path: Path = ROOT / "backend" / "data" / "local" / "users.db"
    auth_secret: str = ""  # signs login tokens; empty → random per process (dev only)
    # sign-up verification codes (Gmail: SMTP_USER = the address, SMTP_PASSWORD = an app password)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465  # implicit TLS
    smtp_user: str = ""  # empty → dev: codes are logged; prod: email sign-up is unavailable
    smtp_password: str = ""

    @property
    def email_ready(self) -> bool:
        return bool(self.smtp_user and self.smtp_password)

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
