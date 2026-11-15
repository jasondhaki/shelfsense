"""Open Food Facts product metadata for the barcodes in sku_base.json.

Responses are cached in data/raw/off/<barcode>.json; a cached barcode is never re-fetched.
Missing product / field -> null (UI shows "n/a")."""

import time

import httpx

from scripts._common import RAW, SKU_BASE, USER_AGENT, read_json, write_json

API = "https://world.openfoodfacts.org/api/v2/product/{}.json"
FIELDS = "product_name,nutriscore_grade,packaging,packaging_tags,categories_tags"


def fetch(barcode: str) -> dict | None:
    cache = RAW / "off" / f"{barcode}.json"
    if cache.exists():
        return read_json(cache)
    for attempt in range(2):
        try:
            r = httpx.get(
                API.format(barcode),
                params={"fields": FIELDS},
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
            if r.status_code == 200:
                write_json(cache, r.json())
                return r.json()
            print(f"  OFF {barcode}: HTTP {r.status_code}")
        except httpx.HTTPError as e:
            print(f"  OFF {barcode}: {e}")
        time.sleep(3 * (attempt + 1))
    return None


def off_fields(barcode: str | None) -> dict:
    out = {"barcode": barcode, "product_name": None, "nutri_score": None, "packaging": None}
    if not barcode:
        return out
    resp = fetch(barcode)
    p = (resp or {}).get("product") or {}
    grade = (p.get("nutriscore_grade") or "").lower()
    out["product_name"] = p.get("product_name") or None
    out["nutri_score"] = grade if grade in {"a", "b", "c", "d", "e"} else None
    out["packaging"] = p.get("packaging") or None
    return out


def build() -> dict[str, dict]:
    print("Open Food Facts")
    result = {}
    for s in read_json(SKU_BASE)["skus"]:
        result[s["sku_id"]] = off_fields(s.get("barcode"))
        print(f"  {s['sku_id']}: {result[s['sku_id']]}")
        time.sleep(1)  # be gentle
    return result


if __name__ == "__main__":
    build()
