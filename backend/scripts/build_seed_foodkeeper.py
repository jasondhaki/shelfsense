"""USDA FSIS FoodKeeper -> data/seed/foodkeeper.json + data/rag/corpus/foodkeeper_<sku>.md

Needs data/raw/foodkeeper/foodkeeper.json (download it yourself from
https://catalog.data.gov/dataset/fsis-foodkeeper-data — FSIS blocks automated downloads).

sl_nominal_hours = LOWER bound of the storage range (DATA_SOURCES §1): refrigerator, or pantry
for bananas / bread / avocados / tomatoes."""

import re

from scripts._common import CORPUS, RAW, SEED, SKU_BASE, read_json, write_json

RAW_FILE = RAW / "foodkeeper" / "foodkeeper.json"
SOURCE_URL = "https://catalog.data.gov/dataset/fsis-foodkeeper-data"
PANTRY = {"BANA-01", "SOUR-01", "AVOC-01", "TOMA-01"}
HOURS = {"hour": 1, "day": 24, "week": 168, "month": 720, "year": 8760}


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


def _match(rows: list[dict], keywords: list[str], storage: str) -> dict | None:
    def text(r):
        return " ".join(str(r.get(k) or "") for k in ("Name", "Name_subtitle", "Keywords")).lower()

    for kw in keywords:  # keyword order = preference order
        hits = [r for r in rows if kw in text(r) and r.get(f"{storage}_Min") is not None]
        if hits:
            # prefer the plainest record (shortest name+subtitle), deterministic
            def plain(r):
                return len(f"{r.get('Name') or ''} {r.get('Name_subtitle') or ''}".strip())

            return min(hits, key=lambda r: (plain(r), r.get("ID") or 0))
    return None


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
    for s in read_json(SKU_BASE)["skus"]:
        sid = s["sku_id"]
        storage = "Pantry" if sid in PANTRY else "Refrigerate"
        r = _match(rows, s["foodkeeper_keywords"], storage)
        if r is None:
            print(f"  {sid}: no FoodKeeper match for {s['foodkeeper_keywords']} ({storage})")
            continue
        lo, hi, metric = (
            r.get(f"{storage}_Min"),
            r.get(f"{storage}_Max"),
            r.get(f"{storage}_Metric"),
        )
        hours = _to_hours(lo, metric)
        name = " — ".join(x for x in (r.get("Name"), r.get("Name_subtitle")) if x)
        tips = r.get(f"{storage}_tips") or ""
        out[sid] = {
            "sku_id": sid,
            "foodkeeper_id": r.get("ID"),
            "name": name,
            "storage": storage.lower(),
            "min": lo,
            "max": hi,
            "metric": metric,
            "tips": tips,
            "sl_nominal_hours": hours,
        }
        print(f"  {sid}: #{r.get('ID')} {name!r} {storage} {lo}-{hi} {metric} -> {hours} h")
        CORPUS.mkdir(parents=True, exist_ok=True)
        (CORPUS / f"foodkeeper_{sid}.md").write_text(
            f"---\nsource: USDA FoodKeeper\ntitle: {name} — {storage.lower()} storage\n"
            f"url: {SOURCE_URL}\nsku_ids: [{sid}]\n---\n"
            f"{name}: store in the {storage.lower()} for {lo}–{hi} {str(metric).lower()}. "
            f"{tips}\n",
            encoding="utf-8",
        )
    write_json(SEED / "foodkeeper.json", list(out.values()))
    return out


if __name__ == "__main__":
    build()
