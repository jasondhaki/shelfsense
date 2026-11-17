"""Build the RAG corpus + indexes (AI_PIPELINE §2).

    uv run python -m scripts.build_rag_index            # corpus, chunks, bm25, graph (offline)
    uv run python -m scripts.build_rag_index --contextual-llm   # LLM-written chunk context
    uv run python -m scripts.build_rag_index --vector   # also index.npz (1 batched Gemini call)

Corpus = FoodKeeper chunks (from build_seed_foodkeeper) + hand-written cited notes + chunks
generated here from the committed seed files (Open Food Facts, ethylene, FAO).

Chunking is semantic and variable-size; every chunk gets a context sentence that is indexed with
it (contextual retrieval, AI_PIPELINE §2.2); graph.json links SKUs, categories, ethylene classes,
documents and sources (graph RAG)."""

import argparse
import asyncio
import re

from app.rag.retriever import tokenize
from scripts._common import BACKEND, CORPUS, RAW, SEED, read_json, write_json

RAG = BACKEND / "data" / "rag"
MIN_CHARS, MAX_CHARS = 150, 600  # variable chunk size bounds
BREAK_OVERLAP = 0.2  # a sentence sharing < 20% of its words with the chunk starts a new topic
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")
CONTEXT_PROMPT = (
    "Here is a document:\n<document>\n{doc}\n</document>\nHere is a chunk from it:\n<chunk>\n"
    "{chunk}\n</chunk>\nWrite one short sentence that situates this chunk within the document "
    "(product, source, topic) to improve search retrieval of the chunk. Answer with only the "
    "sentence."
)


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
    """Semantic, variable-size chunks: sentences join the running chunk while they keep its
    topic (word overlap); a topic shift closes a chunk of MIN_CHARS+, MAX_CHARS always does."""
    out, cur, words = [], "", set()
    for para in [p.strip() for p in body.split("\n\n") if p.strip()]:
        for sent in SENTENCE.split(para):
            toks = set(tokenize(sent))
            overlap = len(toks & words) / len(toks) if toks and words else 1.0
            too_long = len(cur) + len(sent) > MAX_CHARS
            if cur and (too_long or (overlap < BREAK_OVERLAP and len(cur) >= MIN_CHARS)):
                out.append(cur)
                cur, words = sent, toks
            else:
                cur = f"{cur} {sent}" if cur else sent
                words |= toks
    return out + ([cur] if cur else [])


def context_line(meta: dict, names: dict[str, str]) -> str:
    """Offline context: where the chunk comes from and what it is about."""
    about = ", ".join(names[i] for i in meta["sku_ids"] if i in names)
    tail = f", about {about}." if about else ", general guidance for all products."
    return f"From {meta['source']}, '{meta['title']}'{tail}"


def build_chunks(llm_context: bool = False) -> list[dict]:
    names = {s["sku_id"]: s["name"] for s in read_json(SEED / "skus.json")["skus"]}
    old = RAG / "chunks.json"  # reuse LLM contexts for unchanged chunks: no repeat calls
    reuse = {
        c["text"]: c["context"]
        for c in (read_json(old) if old.exists() else [])
        if c.get("context_by") == "llm"
    }
    chunks = []
    for f in sorted(CORPUS.glob("*.md")):
        meta, body = parse(f)
        for i, text in enumerate(chunk(body)):
            c = {"id": f"{f.stem}#{i}", **meta, "text": text}
            c["context"], c["context_by"] = context_line(meta, names), "metadata"
            if text in reuse:
                c["context"], c["context_by"] = reuse[text], "llm"
            elif llm_context:
                ctx = asyncio.run(_llm_context(body, text))
                if ctx:
                    c["context"], c["context_by"] = ctx, "llm"
            chunks.append(c)
    return chunks


async def _llm_context(doc: str, text: str) -> str | None:
    from app.config import get_settings
    from app.services import llm

    out = await llm.generate(
        "You write retrieval context for document chunks.",
        CONTEXT_PROMPT.format(doc=doc, chunk=text),
        get_settings(),
        max_tokens=80,
    )
    await asyncio.sleep(4)  # free-tier requests-per-minute
    return " ".join(out.split()) if out else None


def build_graph(chunks: list[dict]) -> dict:
    """Knowledge graph for graph RAG (and the optional Neo4j mirror)."""
    skus = read_json(SEED / "skus.json")["skus"]
    eth = read_json(SEED / "ethylene.json")["skus"]
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def edge(a: str, b: str, kind: str) -> None:
        edges.append({"source": a, "target": b, "type": kind})

    for s in skus:
        sid, cls = s["sku_id"], eth[s["sku_id"]]["class"]
        nodes[f"sku:{sid}"] = {
            "type": "Sku",
            "name": s["name"],
            "category": s["category"],
            "shelf_life_hours": s["sl_nominal_hours"],
            "ethylene": cls,
        }
        nodes[f"category:{s['category']}"] = {"type": "Category", "name": s["category"]}
        nodes[f"ethylene:{cls}"] = {"type": "EthyleneClass", "name": cls}
        edge(f"sku:{sid}", f"category:{s['category']}", "IN_CATEGORY")
        edge(f"sku:{sid}", f"ethylene:{cls}", "HAS_ETHYLENE_CLASS")
    for a in skus:
        for b in skus:
            if eth[a["sku_id"]]["class"] == "producer" and eth[b["sku_id"]]["class"] == "sensitive":
                edge(f"sku:{a['sku_id']}", f"sku:{b['sku_id']}", "CLASHES_WITH")
    for c in chunks:
        doc = f"doc:{c['id'].split('#')[0]}"
        if doc in nodes:
            continue
        nodes[doc] = {"type": "Document", "name": c["title"], "url": c.get("url", "")}
        nodes[f"source:{c['source']}"] = {"type": "Source", "name": c["source"]}
        edge(doc, f"source:{c['source']}", "PUBLISHED_BY")
        for i in c["sku_ids"]:
            edge(doc, f"sku:{i}", "DESCRIBES")
    return {"nodes": [{"id": k, **v} for k, v in nodes.items()], "edges": edges}


async def embed_all(chunks: list[dict]) -> None:
    import numpy as np

    from app.config import get_settings
    from app.services import gemini

    vecs = await gemini.embed([f"{c['context']}\n{c['text']}" for c in chunks], get_settings())
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
    ap.add_argument(
        "--contextual-llm",
        action="store_true",
        help="write chunk context with the configured LLM (1 call per new chunk)",
    )
    a = ap.parse_args()
    generate_from_seed()
    chunks = build_chunks(a.contextual_llm)
    write_json(RAG / "chunks.json", chunks)
    write_json(
        RAG / "bm25.json",
        {c["id"]: tokenize(f"{c['title']} {c['context']} {c['text']}") for c in chunks},
    )
    graph = build_graph(chunks)
    write_json(RAG / "graph.json", graph)
    n_llm = sum(c["context_by"] == "llm" for c in chunks)
    print(
        f"  {len(chunks)} chunks from {len(list(CORPUS.glob('*.md')))} files "
        f"({n_llm} with LLM context); graph {len(graph['nodes'])} nodes, "
        f"{len(graph['edges'])} edges"
    )
    if a.vector:
        asyncio.run(embed_all(chunks))


if __name__ == "__main__":
    main()
