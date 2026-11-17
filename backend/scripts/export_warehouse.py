"""Export simulated weeks to a local analytics warehouse: Parquet tables + a DuckDB file.

    uv run --group seed python -m scripts.export_warehouse            # seeds 1-20 + demo
    uv run --group seed python -m scripts.export_warehouse --seeds 1-50

Writes backend/data/warehouse/{runs,daily,sku_waste}.parquet and shelfsense.duckdb (git-ignored),
then prints a summary query. Open the .duckdb file in DuckDB, or the Parquet files in any
lakehouse engine."""

import argparse

import duckdb

from app.reports import week_report
from scripts._common import BACKEND

OUT = BACKEND / "data" / "warehouse"


def rows(lo: int, hi: int) -> tuple[list, list, list]:
    runs, daily, skus = [], [], []
    plan = [(s, "none") for s in range(lo, hi + 1)] + [(42, "demo")]
    for seed, scenario in plan:
        r = week_report(seed, scenario)
        k = r["kpis"]
        runs.append(
            (
                seed,
                scenario,
                k["waste_reduction_pct"],
                k["waste_kg_a"],
                k["waste_kg_b"],
                k["food_diverted_kg"],
                k["co2e_avoided_kg"],
                k["net_margin_recovered_usd"],
            )
        )
        daily += [
            (
                seed,
                scenario,
                d["day"],
                d["waste_kg_a"],
                d["waste_kg_b"],
                d["revenue_a"],
                d["revenue_b"],
            )
            for d in r["daily"]
        ]
        skus += [(seed, scenario, sid, u["A"], u["B"]) for sid, u in r["wasted_units"].items()]
    return runs, daily, skus


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="1-20")
    lo, hi = map(int, ap.parse_args().seeds.split("-"))
    runs, daily, skus = rows(lo, hi)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "shelfsense.duckdb").unlink(missing_ok=True)
    con = duckdb.connect(str(OUT / "shelfsense.duckdb"))
    con.execute(
        "CREATE TABLE runs (seed INT, scenario TEXT, waste_reduction_pct DOUBLE, "
        "waste_kg_a DOUBLE, waste_kg_b DOUBLE, food_diverted_kg DOUBLE, co2e_avoided_kg DOUBLE, "
        "net_margin_recovered_usd DOUBLE)"
    )
    con.execute(
        "CREATE TABLE daily (seed INT, scenario TEXT, day INT, waste_kg_a DOUBLE, "
        "waste_kg_b DOUBLE, revenue_a DOUBLE, revenue_b DOUBLE)"
    )
    con.execute(
        "CREATE TABLE sku_waste (seed INT, scenario TEXT, sku_id TEXT, units_a INT, units_b INT)"
    )
    con.executemany("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)", runs)
    con.executemany("INSERT INTO daily VALUES (?,?,?,?,?,?,?)", daily)
    con.executemany("INSERT INTO sku_waste VALUES (?,?,?,?,?)", skus)
    for t in ("runs", "daily", "sku_waste"):
        con.execute(f"COPY {t} TO '{(OUT / f'{t}.parquet').as_posix()}' (FORMAT parquet)")
    print(
        con.sql(
            "SELECT scenario, count(*) AS runs, round(avg(waste_reduction_pct), 1) AS mean_pct,"
            " round(stddev(waste_reduction_pct), 1) AS sd, round(sum(food_diverted_kg), 1) AS kg"
            " FROM runs GROUP BY scenario ORDER BY scenario"
        )
    )
    print(
        con.sql(
            "SELECT sku_id, sum(units_a) AS wasted_a, sum(units_b) AS wasted_b FROM sku_waste "
            "WHERE scenario = 'none' GROUP BY sku_id ORDER BY wasted_a DESC"
        )
    )
    con.close()
    print(f"  wrote {OUT}")


if __name__ == "__main__":
    main()
