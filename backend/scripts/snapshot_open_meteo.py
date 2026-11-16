"""Rebuild data/seed/weather_snapshot.json from Open-Meteo (e.g. a Dhaka store).

    uv run python -m scripts.snapshot_open_meteo [--lat 23.8103 --lon 90.4125 --name "Dhaka, BD"]

Same schema as scripts/snapshot_noaa.py, so the engine is unchanged. Re-running changes the
simulation baseline (the snapshot is what tests and the demo use)."""

import argparse
from datetime import UTC, datetime

import httpx

from app.services.open_meteo import RAIN_CODES, URL, describe, params
from scripts._common import RAW, SEED, USER_AGENT, write_json


def summarise(d: dict, days: int = 7) -> dict:
    h = d["hourly"]
    by_day: dict[str, float] = {}
    for t, pop, code in zip(
        h["time"], h["precipitation_probability"], h["weather_code"], strict=True
    ):
        rainy = code in RAIN_CODES
        by_day[t[:10]] = max(by_day.get(t[:10], 0.0), (pop or 0) / 100 if rainy else 0.0)
    dates = sorted(by_day)[:days]
    rh = [x for x in h["relative_humidity_2m"][:24] if x is not None]
    cur = d["current"]
    return {
        "dates": dates,
        "p_heavy_rain_by_day": [round(by_day[x], 2) for x in dates] + [0.0] * (days - len(dates)),
        "relative_humidity_pct": round(sum(rh) / len(rh), 1) if rh else 60.0,
        "temperature_f": cur.get("temperature_2m"),
        "precip_probability_pct": h["precipitation_probability"][0],
        "short_forecast": describe(cur.get("weather_code")),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=23.8103)
    ap.add_argument("--lon", type=float, default=90.4125)
    ap.add_argument("--name", default="Dhaka, BD")
    a = ap.parse_args()
    r = httpx.get(
        URL, params=params(a.lat, a.lon, days=7), headers={"User-Agent": USER_AGENT}, timeout=15
    )
    r.raise_for_status()
    d = r.json()
    write_json(RAW / "open_meteo" / "forecast.json", d)
    write_json(
        SEED / "weather_snapshot.json",
        {
            "source": "Open-Meteo forecast",
            "location": f"{a.name} ({a.lat}, {a.lon})",
            "retrieved_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            **summarise(d),
        },
    )


if __name__ == "__main__":
    main()
