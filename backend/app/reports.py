"""Headless week reports for the outbound API, the MCP server and automation (n8n, CI).
Deterministic (rule 1), so results are cached by their inputs."""

import statistics
from functools import lru_cache

from app.sim import kpi
from app.sim.cli import load_config, run
from app.sim.state import CYCLE_TICKS


@lru_cache(maxsize=64)
def week_report(seed: int = 42, scenario: str = "demo", hours: int = CYCLE_TICKS) -> dict:
    state, logs = run(load_config(seed), hours, scenario)
    return {
        "seed": seed,
        "scenario": scenario,
        "hours": hours,
        "kpis": kpi.kpis(state),
        "stores": kpi.store_totals(state),
        "daily": [
            {
                "day": p["tick"] // 24 + 1,
                "waste_kg_a": round(p["waste_kg_a"], 2),
                "waste_kg_b": round(p["waste_kg_b"], 2),
                "revenue_a": round(p["revenue_a"], 2),
                "revenue_b": round(p["revenue_b"], 2),
            }
            for p in state.chart[23::24]
        ],
        "wasted_units": {
            sid: {"A": state.a.wasted[sid], "B": state.b.wasted[sid]} for sid in state.a.wasted
        },
        "log_entries": len(logs),
    }


def benchmark(lo: int = 1, hi: int = 20, scenario: str = "none") -> dict:
    vals = [
        v
        for s in range(lo, hi + 1)
        if (v := week_report(s, scenario)["kpis"]["waste_reduction_pct"]) is not None
    ]
    return {
        "seeds": f"{lo}-{hi}",
        "scenario": scenario,
        "n": len(vals),
        "mean_waste_reduction_pct": round(statistics.mean(vals), 1) if vals else None,
        "std": round(statistics.stdev(vals), 1) if len(vals) > 1 else None,
    }
