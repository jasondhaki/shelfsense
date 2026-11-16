"""Build the RAG corpus + indexes (AI_PIPELINE §2).

    uv run python -m scripts.build_rag_index            # corpus + chunks.json + bm25.json (offline)
    uv run python -m scripts.build_rag_index --vector   # also index.npz (1 batched Gemini call)

Corpus = FoodKeeper chunks (from build_seed_foodkeeper) + hand-written cited notes + chunks
generated here from the committed seed files (Open Food Facts, ethylene, FAO)."""

import argparse
import asyncio

from app.rag.retriever import tokenize
from scripts._common import BACKEND, CORPUS, RAW, SEED, read_json, write_json

RAG = BACKEND / "data" / "rag"
CHUNK_CHARS = 500


def _md(path, source: str, title: str, url: str, sku_ids: list[str], body: str) -> None:
    path.write_text(
        f"---\nsource: {source}\ntitle: {title}\nurl: {url}\nsku_ids: [{', '.join(sku_ids)}]\n"
        f"---\n{body.strip()}\n",
        encoding="utf-8",
    )


def generate_from_seed() -> None:
    skus = read_json(SEED / "skus.json")["skus"]
    eth = read_json(SEED / "ethylene.json")
    fao = read_json(SEED / "faostat.json")
    for s in skus:
        o = s["off"]
        if o["barcode"]:
            raw = RAW / "off" / f"{o['barcode']}.json"
            cats = []
            if raw.exists():
                cats = (read_json(raw).get("product") or {}).get("categories_tags") or []
            _md(
                CORPUS / f"off_{s['sku_id']}.md",
                "Open Food Facts",
                f"{s['name']} — product metadata",
                f"https://world.openfoodfacts.org/product/{o['barcode']}",
                [s["sku_id"]],
                f'Reference product for {s["name"]}: "{o["product_name"]}" (barcode '
                f"{o['barcode']}). Nutri-Score: {(o['nutri_score'] or 'n/a').upper()}. "
                f"Packaging: {o['packaging'] or 'not recorded'}. Categories: "
                f"{', '.join(c.removeprefix('en:') for c in cats[:6]) or 'not recorded'}. "
                "Data from Open Food Facts (ODbL).",
            )
        e = eth["skus"][s["sku_id"]]
        what = {
            "producer": "an ethylene producer — it can speed ripening and yellowing of "
            "ethylene-sensitive items stored or boxed with it",
            "sensitive": "ethylene-sensitive — keep it away from ethylene producers such as "
            "bananas, avocados and tomatoes",
            "neutral": "neither a notable ethylene producer nor classed as sensitive here",
        }
        src = eth["sources"].get(e.get("source") or "", "")
        _md(
            CORPUS / f"ethylene_{s['sku_id']}.md",
            "ShelfSense ethylene table",
            f"{s['name']} — ethylene class",
            "backend/data/seed/ethylene.json",
            [s["sku_id"]],
            f"{s['name']} is {what[e['class']]}. {e.get('note', '')} Source: {src or 'n/a'}",
        )
    for cat, f in fao["categories"].items():
        ids = [s["sku_id"] for s in skus if s["category"] == cat]
        _md(
            CORPUS / f"fao_{cat}.md",
            "FAO",
            f"Retail waste and CO2e — {cat}",
            "https://www.fao.org/4/mb060e/mb060e.pdf",
            ids,
            f"FAO (2011) estimates that {f['retail_waste_pct']}% of {f['fao_group'].lower()} "
            f"entering supermarket retail in North America and Oceania is lost or wasted there. "
            f"Producing one kilogram emits about {f['co2e_kg_per_kg']} kg CO2e (Poore & Nemecek "
            f"2018, '{f['co2e_item']}').",
        )


def parse(path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    _, head, body = text.split("---\n", 2)
    meta = dict(line.split(": ", 1) for line in head.strip().splitlines())
    ids = meta.get("sku_ids", "[]").strip("[]")
    meta["sku_ids"] = [x.strip() for x in ids.split(",") if x.strip()]
    return meta, body.strip()


def chunk(body: str) -> list[str]:
    """~500 characters on paragraph boundaries."""
    out, cur = [], ""
    for para in [p.strip() for p in body.split("\n\n") if p.strip()]:
        if cur and len(cur) + len(para) > CHUNK_CHARS:
            out.append(cur)
            cur = para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    return out + ([cur] if cur else [])


def build_chunks() -> list[dict]:
    chunks = []
    for f in sorted(CORPUS.glob("*.md")):
        meta, body = parse(f)
        for i, text in enumerate(chunk(body)):
            chunks.append({"id": f"{f.stem}#{i}", **meta, "text": text})
    return chunks


async def embed_all(chunks: list[dict]) -> None:
    import numpy as np

    from app.config import get_settings
    from app.services import gemini

    vecs = await gemini.embed([f"{c['title']}\n{c['text']}" for c in chunks], get_settings())
    if vecs is None:
        raise SystemExit("Embedding failed — check GEMINI_API_KEY / GEMINI_EMBED_MODEL.")
    np.savez(
        RAG / "index.npz",
        embeddings=vecs.astype("float32"),
        ids=np.array([c["id"] for c in chunks]),
    )
    print(f"  wrote data/rag/index.npz ({vecs.shape[0]}×{vecs.shape[1]})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vector", action="store_true", help="also embed with Gemini (1 API call)")
    a = ap.parse_args()
    generate_from_seed()
    chunks = build_chunks()
    write_json(RAG / "chunks.json", chunks)
    write_json(RAG / "bm25.json", {c["id"]: tokenize(f"{c['title']} {c['text']}") for c in chunks})
    print(f"  {len(chunks)} chunks from {len(list(CORPUS.glob('*.md')))} files")
    if a.vector:
        asyncio.run(embed_all(chunks))


if __name__ == "__main__":
    main()
