"""USDA FSIS FoodKeeper -> data/seed/foodkeeper.json + data/rag/corpus/foodkeeper_<sku>.md

Needs data/raw/foodkeeper/foodkeeper.json (download it in a browser from
https://catalog.data.gov/dataset/fsis-foodkeeper-data — FSIS returns 403 to scripts).

Each SKU names its record in sku_base.json: {"foodkeeper": {"id": 481, "field": "DOP_Refrigerate"}}.
Records were picked by hand (keyword matching picked muffins for bananas). `field` is the storage
column to use; DOP_* = "from date of purchase". sl_nominal_hours = the LOWER bound
(DATA_SOURCES §1). field = null -> FoodKeeper gives no number; the base value is kept."""

import re

from scripts._common import CORPUS, RAW, SEED, SKU_BASE, read_json, write_json

RAW_FILE = RAW / "foodkeeper" / "foodkeeper.json"
SOURCE_URL = "https://catalog.data.gov/dataset/fsis-foodkeeper-data"
HOURS = {"hour": 1, "day": 24, "week": 168, "month": 720, "year": 8760}
STORAGE = {"Pantry": "pantry", "Refrigerate": "refrigerator", "DOP_Refrigerate": "refrigerator"}


def _rows(doc: dict) -> list[dict]:
    """FoodKeeper JSON stores each row as a list of single-key dicts; flatten them."""
    sheets = doc.get("sheets") if isinstance(doc, dict) else None
    if not sheets:
        raise SystemExit(f"Unexpected FoodKeeper layout; top-level keys: {list(doc)[:10]}")
    sheet = next((s for s in sheets if s.get("name", "").lower() == "product"), None)
    if sheet is None:
        raise SystemExit(f"No 'Product' sheet; sheets: {[s.get('name') for s in sheets]}")
    return [{k: v for cell in row for k, v in cell.items()} for row in sheet["data"]]


def _to_hours(n, metric) -> float | None:
    if n is None or not metric:
        return None
    unit = re.sub(r"s$", "", str(metric).strip().lower())
    return float(n) * HOURS[unit] if unit in HOURS else None


def record(rows: list[dict], fk_id: int, field: str | None) -> dict:
    r = next((r for r in rows if r.get("ID") is not None and int(r["ID"]) == fk_id), None)
    if r is None:
        raise SystemExit(f"FoodKeeper record #{fk_id} not found")
    name = " — ".join(x for x in (r.get("Name", "").strip(), r.get("Name_subtitle")) if x)
    if field is None:  # no numeric storage time, e.g. milk: "Package use-by date"
        metric = r.get("Refrigerate_Metric") or r.get("Pantry_Metric")
        return {
            "foodkeeper_id": fk_id,
            "name": name,
            "storage": None,
            "min": None,
            "max": None,
            "metric": metric,
            "tips": "",
            "sl_nominal_hours": None,
        }
    lo, hi, metric = r.get(f"{field}_Min"), r.get(f"{field}_Max"), r.get(f"{field}_Metric")
    hours = _to_hours(lo, metric)
    if hours is None:
        raise SystemExit(f"#{fk_id} {name}: no numeric {field} value ({lo}, {metric})")
    tips = r.get(f"{field}_tips") or ""
    return {
        "foodkeeper_id": fk_id,
        "name": name,
        "storage": STORAGE.get(field, field),
        "from_purchase": field.startswith("DOP_"),
        "min": lo,
        "max": hi,
        "metric": metric,
        "tips": tips,
        "sl_nominal_hours": hours,
    }


def build() -> dict[str, dict] | None:
    print("USDA FoodKeeper")
    if not RAW_FILE.exists():
        print(
            f"  SKIPPED — {RAW_FILE.relative_to(RAW.parent.parent)} not found. "
            f"Download foodkeeper.json from {SOURCE_URL}"
        )
        return None
    try:
        doc = read_json(RAW_FILE)
    except ValueError:
        raise SystemExit(f"{RAW_FILE} is not JSON (an HTML error page?). Re-download it.") from None
    rows = _rows(doc)
    out = {}
    CORPUS.mkdir(parents=True, exist_ok=True)
    for s in read_json(SKU_BASE)["skus"]:
        sid = s["sku_id"]
        rec = {"sku_id": sid, **record(rows, s["foodkeeper"]["id"], s["foodkeeper"]["field"])}
        out[sid] = rec
        lo, hi, metric, where = rec["min"], rec["max"], rec["metric"], rec["storage"]
        print(
            f"  {sid}: #{rec['foodkeeper_id']} {rec['name']!r} {where} {lo}-{hi} {metric} "
            f"-> {rec['sl_nominal_hours']} h"
        )
        span = (
            f"store in the {where} for {lo:g}–{hi:g} {str(metric).lower()}"
            + (" from the date of purchase" if rec.get("from_purchase") else "")
            if where
            else f"storage time: {metric}"
        )
        (CORPUS / f"foodkeeper_{sid}.md").write_text(
            f"---\nsource: USDA FoodKeeper\ntitle: {rec['name']} — storage\n"
            f"url: {SOURCE_URL}\nsku_ids: [{sid}]\n---\n"
            f"{rec['name']}: {span}. {rec['tips']}\n",
            encoding="utf-8",
        )
    write_json(SEED / "foodkeeper.json", list(out.values()))
    return out


if __name__ == "__main__":
    build()
