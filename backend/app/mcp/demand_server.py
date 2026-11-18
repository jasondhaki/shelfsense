"""MCP server `shelfsense-demand`: the DEMAND_AGENT's inputs — weather and hourly demand forecast.

uv run python -m app.mcp.demand_server            # stdio
uv run python -m app.mcp.demand_server --http     # streamable HTTP, http://127.0.0.1:8769/mcp
"""

import asyncio
from typing import Literal

from mcp.server.mcpserver import MCPServer

from app.config import get_settings
from app.mcp import serve
from app.services.noaa import NoaaService
from app.services.open_meteo import OpenMeteoService
from app.sim.cli import load_config, run
from app.sim.demand import lam, storm_active
from app.sim.state import CYCLE_TICKS

server = MCPServer(
    "shelfsense-demand",
    instructions="Weather and the simulation's expected hourly demand per SKU (Favorita weekday "
    "pattern × weather × events). Live weather falls back to a recorded snapshot.",
)


@server.tool()
def weather_now() -> dict:
    """Current weather from the configured provider (Open-Meteo or NOAA), or the snapshot."""
    s = get_settings()
    svc = OpenMeteoService(s) if s.weather_provider == "open_meteo" else NoaaService(s)
    asyncio.run(svc.refresh())
    return {"source": svc.source, **svc.current()}


@server.tool()
def demand_forecast(
    sku_id: str,
    from_hour: int = 0,
    hours: int = 24,
    seed: int = 42,
    scenario: Literal["none", "demo"] = "demo",
) -> dict:
    """Expected units per hour (λ, before price effects) for one SKU over a window of the week."""
    cfg = load_config(seed)
    sku = cfg.sku_by_id.get(sku_id)
    if sku is None:
        raise ValueError(f"Unknown SKU {sku_id}; known: {', '.join(cfg.sku_by_id)}.")
    start = max(0, min(from_hour, CYCLE_TICKS - 1))
    end = min(CYCLE_TICKS, start + max(1, min(hours, CYCLE_TICKS)))
    state, _ = run(cfg, max(1, end), scenario)  # events (e.g. the storm) are in the state
    per_hour = [
        {"hour": t, "units": round(lam(state, sku, t), 2), "storm": storm_active(state, t)}
        for t in range(start, end)
    ]
    return {
        "sku_id": sku_id,
        "total_units": round(sum(h["units"] for h in per_hour), 1),
        "hourly": per_hour,
    }


if __name__ == "__main__":
    serve(server, 8769)
