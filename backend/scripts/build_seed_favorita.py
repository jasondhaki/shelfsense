"""Kaggle Corporación Favorita -> aggregates only, merged into data/seed/sales_profile.json.

Needs (download with your own Kaggle account; never committed — competition licence):
  data/raw/favorita/train.csv   (~4.7 GB; read in chunks)
  data/raw/favorita/items.csv
from https://www.kaggle.com/competitions/favorita-grocery-sales-forecasting/data

Outputs per family: dow_weight[Mon..Sun] (mean daily family units by weekday / overall mean),
mean units per store-item-day, promo_lift (on-promo / off-promo mean; a sanity check next to the
assumed elasticity, NOT an elasticity). hour_share stays an assumed curve (Favorita is daily).
Run:  uv run --group seed python -m scripts.build_seed_favorita"""

from scripts._common import RAW, SEED, SKU_BASE, read_json, write_json

DIR = RAW / "favorita"
FAMILIES = {"PRODUCE", "DAIRY", "BREAD/BAKERY", "SEAFOOD"}
URL = "https://www.kaggle.com/competitions/favorita-grocery-sales-forecasting/data"


def build(chunksize: int = 5_000_000) -> dict | None:
    print("Kaggle Favorita")
    if not (DIR / "train.csv").exists() or not (DIR / "items.csv").exists():
        print(f"  SKIPPED — put train.csv and items.csv in data/raw/favorita/ (from {URL})")
        return None
    import pandas as pd  # seed-only dependency

    items = pd.read_csv(DIR / "items.csv", usecols=["item_nbr", "family"])
    items = items[items["family"].isin(FAMILIES)].set_index("item_nbr")["family"]
    daily, promo = [], []
    reader = pd.read_csv(
        DIR / "train.csv",
        usecols=["date", "item_nbr", "unit_sales", "onpromotion"],
        dtype={"item_nbr": "int64", "unit_sales": "float32"},
        chunksize=chunksize,
    )
    for i, ch in enumerate(reader):
        ch["family"] = ch["item_nbr"].map(items)
        ch = ch.dropna(subset=["family"])
        ch = ch[ch["unit_sales"] > 0]  # negative = returns
        daily.append(ch.groupby(["date", "family"])["unit_sales"].sum())
        p = ch.dropna(subset=["onpromotion"])
        promo.append(
            p.groupby(["family", p["onpromotion"].astype(bool)])["unit_sales"].agg(["sum", "count"])
        )
        promo.append(
            ch.groupby(["family"])["unit_sales"]
            .agg(["sum", "count"])
            .assign(onpromotion="all")
            .set_index("onpromotion", append=True)
        )
        print(f"  chunk {i + 1}", end="\r")
    d = pd.concat(daily).groupby(level=[0, 1]).sum().reset_index()
    d["dow"] = pd.to_datetime(d["date"]).dt.dayofweek  # Monday = 0, matches start_dow
    pr = pd.concat(promo).groupby(level=[0, 1]).sum()
    out = {}
    for fam, g in d.groupby("family"):
        by_dow = g.groupby("dow")["unit_sales"].mean()

        def mean(k, fam=fam):
            return pr.loc[(fam, k), "sum"] / pr.loc[(fam, k), "count"]

        lift = mean(True) / mean(False) if (fam, True) in pr.index else None
        out[fam] = {
            "dow_weight": [round(float(by_dow[i] / by_dow.mean()), 4) for i in range(7)],
            "mean_units_per_store_item_day": round(float(mean("all")), 2),
            "promo_lift": round(float(lift), 3) if lift is not None else None,
        }
        print(f"  {fam}: {out[fam]}")
    profile = read_json(SEED / "sales_profile.json")
    profile["favorita"] = out
    cat_family = {s["category"]: s["favorita_family"] for s in read_json(SKU_BASE)["skus"]}
    profile["dow_weight"] = {"default": [1.0] * 7} | {
        c: out[f]["dow_weight"] for c, f in cat_family.items() if f in out
    }
    profile["_note"] = (
        "dow_weight per category from Kaggle Favorita family aggregates (see favorita block). "
        "hour_share is an ASSUMED typical grocery traffic curve (open 07:00-21:59); raw weights, "
        "normalised on load."
    )
    write_json(SEED / "sales_profile.json", profile)
    return out


if __name__ == "__main__":
    build()
