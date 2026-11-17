"""MCP server `shelfsense-sim`: run the deterministic twin-store week headlessly.

uv run python -m app.mcp.sim_server            # stdio
uv run python -m app.mcp.sim_server --http     # streamable HTTP, http://127.0.0.1:8765/mcp
"""

from typing import Literal

from mcp.server.mcpserver import MCPServer

from app import reports, views
from app.mcp import serve
from app.sim.cli import load_config, run
from app.sim.state import CYCLE_TICKS

server = MCPServer(
    "shelfsense-sim",
    instructions="ShelfSense twin-store food-waste simulation. Store A is the baseline, Store B "
    "uses ShelfSense. Same seed + scenario always gives the same result. Numbers are simulated.",
)
Scenario = Literal["none", "demo"]


@server.tool()
def run_week(seed: int = 42, scenario: Scenario = "demo", hours: int = CYCLE_TICKS) -> dict:
    """Run both stores for `hours` (max 168) and return KPIs, store totals, daily waste and
    wasted units per SKU. scenario=demo adds the rainstorm, cold-chain delay and damaged scan."""
    return reports.week_report(seed, scenario, max(1, min(hours, CYCLE_TICKS)))


@server.tool()
def benchmark(first_seed: int = 1, last_seed: int = 20, scenario: Scenario = "none") -> dict:
    """Mean ± std waste reduction of Store B vs Store A over a seed range (max 50 seeds)."""
    last_seed = min(last_seed, first_seed + 49)
    return reports.benchmark(first_seed, last_seed, scenario)


@server.tool()
def list_skus() -> list[dict]:
    """The eight perishable products: id, name, category, nominal shelf life, base price."""
    return [
        {
            "sku_id": s.sku_id,
            "name": s.name,
            "category": s.category,
            "shelf_life_hours": s.sl_nominal_hours,
            "base_price_usd": s.base_price_usd,
        }
        for s in load_config().skus
    ]


@server.tool()
def price_formula(sku_id: str, hour: int = 96, seed: int = 42, scenario: Scenario = "demo") -> dict:
    """Step-by-step markdown formula for one SKU in Store B at a given simulated hour."""
    state, _ = run(load_config(seed), max(1, min(hour, CYCLE_TICKS)), scenario)
    sku = state.config.sku_by_id.get(sku_id)
    if sku is None:
        raise ValueError(f"Unknown SKU {sku_id}; call list_skus.")
    return views.formula(state, sku).model_dump()


if __name__ == "__main__":
    serve(server, 8765)
