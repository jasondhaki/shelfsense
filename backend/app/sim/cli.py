"""Headless runner + seed-file loader.

    uv run python -m app.sim.cli --hours 168 --seed 42 [--scenario demo] [--seeds 1-20]

The loader lives here (not in the engine) because it reads files; the engine stays I/O-free.
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from app.sim import engine, kpi
from app.sim.events import Event
from app.sim.shelf_life import alpha_from_vision
from app.sim.state import CYCLE_TICKS, LogDraft, SimConfig, SimState, SkuConfig

SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


def load_config(seed: int = 42, seed_dir: Path = SEED_DIR, **overrides) -> SimConfig:
    def read(name: str) -> dict:
        return json.loads((seed_dir / name).read_text(encoding="utf-8"))

    skus = [SkuConfig.from_dict(d) for d in read("skus.json")["skus"]]
    profile = read("sales_profile.json")
    weather = read("weather_snapshot.json")
    fao = read("faostat.json")
    cats = {s.category for s in skus}

    def per_cat(table: dict) -> dict:
        return {c: table.get(c, table["default"]) for c in cats}

    hour_share = {}
    for c, w in per_cat(profile["hour_share"]).items():
        total = sum(w)
        hour_share[c] = [x / total for x in w]
    return SimConfig(
        skus=skus,
        hour_share=hour_share,
        dow_weight=per_cat(profile["dow_weight"]),
        co2e_factor={c: fao["categories"][c]["co2e_kg_per_kg"] for c in cats},
        seed=seed,
        rh_base=weather["relative_humidity_pct"],
        p_heavy_rain=list(weather["p_heavy_rain_by_day"]),
        **overrides,
    )


def demo_timeline() -> dict[int, list[Event]]:
    """Scripted demo (SIMULATION_ENGINE §13): rain D2 10:00, cold-chain hitting the D3 06:00
    delivery, thermal-anomaly scan (Frame 3 fixture values) of strawberries D4 14:00."""
    frame3_alpha = alpha_from_vision(3.8, ["mold", "ethylene_bruising", "soft_spots"])
    return {
        24 + 10: [Event("rainstorm")],
        48 + 2: [Event("cold_chain_delay", {"skus": ["STRW-01", "SPIN-01", "SALM-01"]})],
        72 + 14: [
            Event(
                "vision_override",
                {"sku_id": "STRW-01", "alpha": frame3_alpha, "frame_id": "frame3"},
            )
        ],
    }


SCENARIOS = {"none": dict, "demo": demo_timeline}


def run(
    config: SimConfig, hours: int = CYCLE_TICKS, scenario: str = "none"
) -> tuple[SimState, list[LogDraft]]:
    timeline = SCENARIOS[scenario]()
    state = engine.new_sim(config)
    logs: list[LogDraft] = []
    for _ in range(hours):
        state, new = engine.step(state, timeline.get(state.tick, []))
        logs += new
    return state, logs


def _fmt(x: float | None, spec: str = ".1f") -> str:
    return "—" if x is None else format(x, spec)


def _report(state: SimState) -> None:
    print(
        f"{'day':>3} {'waste A kg':>11} {'waste B kg':>11} {'rev A $':>10} {'rev B $':>10} "
        f"{'reduction':>9}"
    )
    for p in state.chart[23::24]:
        wa, wb = p["waste_kg_a"], p["waste_kg_b"]
        red = (wa - wb) / wa * 100 if wa > 0 else None
        print(
            f"{p['tick'] // 24 + 1:>3} {wa:>11.2f} {wb:>11.2f} {p['revenue_a']:>10.2f} "
            f"{p['revenue_b']:>10.2f} {_fmt(red):>8}%"
        )
    k = kpi.kpis(state)
    print(f"\nWaste reduction:       {_fmt(k['waste_reduction_pct'])}%")
    print(f"Food diverted:         {k['food_diverted_kg']:.2f} kg")
    print(f"CO2e avoided:          {k['co2e_avoided_kg']:.2f} kg (Poore & Nemecek 2018)")
    print(f"Net margin recovered:  ${k['net_margin_recovered_usd']:.2f}")
    for name, t in kpi.store_totals(state).items():
        print(
            f"Store {name}: received {t['units_received']}, sold {t['units_sold']}, "
            f"wasted {t['units_wasted']} ({t['waste_kg']:.1f} kg), revenue "
            f"${t['revenue_usd']:.2f}, GM ${t['gross_margin_usd']:.2f}"
        )
    print("\nWasted units by SKU (A / B):")
    for sid in state.a.wasted:
        print(f"  {sid}: {state.a.wasted[sid]:>4} / {state.b.wasted[sid]:>4}")


def calibration_report(
    seeds: range, hours: int = CYCLE_TICKS, scenario: str = "none", **overrides
) -> dict[str, tuple[float, float, float]]:
    """Mean Store A / B waste % per category over seeds, next to FAO's retail figure."""
    fao = json.loads((SEED_DIR / "faostat.json").read_text(encoding="utf-8"))["categories"]
    acc: dict[str, list[tuple[float, float]]] = {}
    for s in seeds:
        st, _ = run(load_config(s, **overrides), hours, scenario)
        for c, v in kpi.category_waste_pct(st).items():
            acc.setdefault(c, []).append((v["A"], v["B"]))
    out = {}
    print(f"{'category':<13} {'FAO retail':>10} {'Store A':>8} {'Store B':>8}")
    for c, vals in sorted(acc.items()):
        a = statistics.mean(v[0] for v in vals)
        b = statistics.mean(v[1] for v in vals)
        out[c] = (fao[c]["retail_waste_pct"], a, b)
        print(f"{c:<13} {fao[c]['retail_waste_pct']:>9.1f}% {a:>7.1f}% {b:>7.1f}%")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="ShelfSense headless simulation")
    ap.add_argument("--hours", type=int, default=CYCLE_TICKS)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--scenario", choices=list(SCENARIOS), default="none")
    ap.add_argument("--seeds", help="range like 1-20: print waste reduction mean ± std")
    ap.add_argument(
        "--calibrate",
        action="store_true",
        help="with --seeds: Store A waste %% by category vs FAO retail figures",
    )
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

    if args.seeds and args.calibrate:
        lo, hi = map(int, args.seeds.split("-"))
        calibration_report(range(lo, hi + 1), args.hours, args.scenario)
        return
    if args.seeds:
        lo, hi = map(int, args.seeds.split("-"))
        vals = []
        for s in range(lo, hi + 1):
            st, _ = run(load_config(s), args.hours, args.scenario)
            k = kpi.kpis(st)
            vals.append(k["waste_reduction_pct"])
            print(
                f"seed {s:>3}: reduction {_fmt(k['waste_reduction_pct'])}%  "
                f"A {k['waste_kg_a']:.1f} kg  B {k['waste_kg_b']:.1f} kg  "
                f"margin ${k['net_margin_recovered_usd']:.2f}"
            )
        ok = [v for v in vals if v is not None]
        if ok:
            sd = statistics.stdev(ok) if len(ok) > 1 else 0.0
            print(f"\nmean {statistics.mean(ok):.1f}% ± {sd:.1f} (n={len(ok)})")
        return

    t0 = time.perf_counter()
    state, logs = run(load_config(args.seed), args.hours, args.scenario)
    dt = time.perf_counter() - t0
    _report(state)
    print(f"\n{len(logs)} log entries, {len(state.event_log)} events, ran in {dt:.2f}s")


if __name__ == "__main__":
    main()
