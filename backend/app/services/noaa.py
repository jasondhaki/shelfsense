"""NOAA api.weather.gov for the header widget, 30-min cache, snapshot fallback.

The simulation itself always uses the committed weather_snapshot.json (determinism); live NOAA
only feeds the display."""

import json
import logging
import time
from pathlib import Path

import httpx

from app.config import Settings

log = logging.getLogger(__name__)
SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "seed" / "weather_snapshot.json"
CACHE_S = 30 * 60


class NoaaService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        self.snapshot = {
            "location": snap.get("location", "snapshot"),
            "temperature_f": snap.get("temperature_f"),
            "precip_probability_pct": snap.get("precip_probability_pct"),
            "short_forecast": snap.get("short_forecast"),
        }
        self.live: dict | None = None
        self.fetched_at = 0.0

    @property
    def source(self) -> str:
        return "live" if self.live else "snapshot"

    def current(self) -> dict:
        return self.live or self.snapshot

    async def refresh(self) -> None:
        """Fetch if enabled and stale. Never raises: on any failure keep the last value."""
        s = self.settings
        if not s.noaa_enabled or time.monotonic() - self.fetched_at < CACHE_S:
            return
        self.fetched_at = time.monotonic()
        headers = {"User-Agent": s.noaa_user_agent, "Accept": "application/geo+json"}
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=s.http_timeout_s, headers=headers) as c:
                    pt = await c.get(f"https://api.weather.gov/points/{s.noaa_lat},{s.noaa_lon}")
                    pt.raise_for_status()
                    props = pt.json()["properties"]
                    hr = await c.get(props["forecastHourly"])
                    hr.raise_for_status()
                p = hr.json()["properties"]["periods"][0]
                loc = props["relativeLocation"]["properties"]
                self.live = {
                    "location": f"{loc['city']}, {loc['state']}",
                    "temperature_f": p.get("temperature"),
                    "precip_probability_pct": (p.get("probabilityOfPrecipitation") or {}).get(
                        "value"
                    ),
                    "short_forecast": p.get("shortForecast"),
                }
                return
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
                log.warning("NOAA fetch failed (attempt %d): %s", attempt + 1, e)
