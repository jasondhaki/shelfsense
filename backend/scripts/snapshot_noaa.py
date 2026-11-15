"""Save a real api.weather.gov hourly forecast as data/seed/weather_snapshot.json.

Run manually; re-running changes the simulation (the snapshot is the deterministic baseline).
    uv run python -m scripts.snapshot_noaa [--lat 40.7128 --lon -74.0060]"""

import argparse
import re
from datetime import UTC, datetime

import httpx

from scripts._common import RAW, SEED, USER_AGENT, write_json

RAIN = re.compile(r"rain|shower|thunder", re.I)


def get(url: str) -> dict:
    r = httpx.get(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"}, timeout=15
    )
    r.raise_for_status()
    return r.json()


def summarise(periods: list[dict], days: int = 7) -> dict:
    """p_heavy_rain per calendar day = max precip probability that day / 100, counted only
    on hours whose shortForecast mentions rain/showers/thunderstorms (DATA_SOURCES §4)."""
    by_day: dict[str, float] = {}
    for p in periods:
        d = p["startTime"][:10]
        pop = (p.get("probabilityOfPrecipitation") or {}).get("value") or 0
        rainy = bool(RAIN.search(p.get("shortForecast", "")))
        by_day[d] = max(by_day.get(d, 0.0), pop / 100 if rainy else 0.0)
    dates = sorted(by_day)[:days]
    rh = [(p.get("relativeHumidity") or {}).get("value") for p in periods[:24]]
    rh = [x for x in rh if x is not None]
    now = periods[0]
    return {
        "dates": dates,
        "p_heavy_rain_by_day": [round(by_day[d], 2) for d in dates] + [0.0] * (days - len(dates)),
        "relative_humidity_pct": round(sum(rh) / len(rh), 1) if rh else 60.0,
        "temperature_f": now.get("temperature"),
        "precip_probability_pct": (now.get("probabilityOfPrecipitation") or {}).get("value"),
        "short_forecast": now.get("shortForecast"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=40.7128)
    ap.add_argument("--lon", type=float, default=-74.0060)
    a = ap.parse_args()
    point = get(f"https://api.weather.gov/points/{a.lat},{a.lon}")
    hourly = get(point["properties"]["forecastHourly"])
    write_json(RAW / "noaa" / "hourly.json", hourly)
    loc = point["properties"]["relativeLocation"]["properties"]
    snap = {
        "source": "NOAA api.weather.gov hourly forecast",
        "location": f"{loc['city']}, {loc['state']} ({a.lat}, {a.lon})",
        "retrieved_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        **summarise(hourly["properties"]["periods"]),
        "hourly": [
            {
                "start": p["startTime"],
                "temperature_f": p.get("temperature"),
                "rh_pct": (p.get("relativeHumidity") or {}).get("value"),
                "pop_pct": (p.get("probabilityOfPrecipitation") or {}).get("value"),
                "short_forecast": p.get("shortForecast"),
            }
            for p in hourly["properties"]["periods"][:72]
        ],
    }
    write_json(SEED / "weather_snapshot.json", snap)


if __name__ == "__main__":
    main()
