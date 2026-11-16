"""Open-Meteo (free, no key, worldwide) for the header widget — same interface as NoaaService.
WEATHER_PROVIDER=open_meteo with OPEN_METEO_LAT/LON (default Dhaka). The simulation itself still
uses the committed weather_snapshot.json; `scripts/snapshot_open_meteo.py` can rebuild it."""

import json
import logging
import time

import httpx

from app.config import Settings
from app.services.noaa import CACHE_S, SNAPSHOT

log = logging.getLogger(__name__)
URL = "https://api.open-meteo.com/v1/forecast"
# WMO weather codes (https://open-meteo.com/en/docs)
WMO = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    80: "Rain showers",
    81: "Rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with hail",
}
RAIN_CODES = set(range(51, 68)) | {80, 81, 82, 95, 96, 99}


def describe(code: int | None) -> str | None:
    return None if code is None else WMO.get(code, f"WMO code {code}")


def params(lat: float, lon: float, days: int = 1) -> dict:
    return {
        "latitude": lat,
        "longitude": lon,
        "temperature_unit": "fahrenheit",
        "timezone": "auto",
        "forecast_days": days,
        "current": "temperature_2m,relative_humidity_2m,weather_code",
        "hourly": "relative_humidity_2m,precipitation_probability,weather_code",
    }


class OpenMeteoService:
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
        s = self.settings
        if not s.noaa_enabled or time.monotonic() - self.fetched_at < CACHE_S:
            return  # NOAA_ENABLED doubles as the live-weather switch for either provider
        self.fetched_at = time.monotonic()
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=s.http_timeout_s) as c:
                    r = await c.get(URL, params=params(s.open_meteo_lat, s.open_meteo_lon))
                    r.raise_for_status()
                d = r.json()
                cur = d["current"]
                pop = (d.get("hourly") or {}).get("precipitation_probability") or [None]
                self.live = {
                    "location": s.open_meteo_location,
                    "temperature_f": cur.get("temperature_2m"),
                    "precip_probability_pct": pop[0],
                    "short_forecast": describe(cur.get("weather_code")),
                }
                return
            except (httpx.HTTPError, KeyError, ValueError) as e:
                log.warning("Open-Meteo fetch failed (attempt %d): %s", attempt + 1, e)
