"""Retrieval evaluation on the hand-labelled set in data/rag/eval.json.

    uv run python -m scripts.eval_rag             # BM25: contextual chunks vs plain chunks
    uv run python -m scripts.eval_rag --vector    # also vector mode (1 batched embed call)

Metrics: hit@3 (a relevant document in the top 3) and MRR (mean reciprocal rank of the first
relevant document)."""

import argparse
import asyncio
import math
from collections import Counter

from app.rag.retriever import RAG, Retriever, tokenize
from scripts._common import read_json


def evaluate(r: Retriever, k: int = 3) -> dict[str, float]:
    qs = read_json(RAG / "eval.json")["queries"]
    hits, rr = 0, 0.0
    for q in qs:
        ranked = [h.chunk_id.split("#")[0] for h in r.retrieve(q["query"], q["sku_id"], k=10)]
        first = next((i for i, d in enumerate(ranked) if d in q["relevant"]), None)
        hits += first is not None and first < k
        rr += 1 / (first + 1) if first is not None else 0
    return {"n": len(qs), f"hit@{k}": round(hits / len(qs), 3), "mrr": round(rr / len(qs), 3)}


def plain(r: Retriever) -> Retriever:
    """The same retriever indexed without the context sentences (the ablation)."""
    r.tf = [Counter(tokenize(f"{c['title']} {c['text']}")) for c in r.chunks]
    r.dl = [sum(t.values()) for t in r.tf]
    r.avgdl = sum(r.dl) / len(r.dl)
    df, n = Counter(t for tf in r.tf for t in tf), len(r.tf)
    r.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
    return r


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vector", action="store_true")
    a = ap.parse_args()
    print("bm25 contextual:", evaluate(Retriever("bm25")))
    print("bm25 plain:     ", evaluate(plain(Retriever("bm25"))))
    if a.vector:
        from app.config import get_settings
        from app.services import gemini

        s = get_settings()
        r = Retriever("vector", vector_ready=True, embed_model=s.gemini_embed_model)
        qs = [q["query"] for q in read_json(RAG / "eval.json")["queries"]]
        asyncio.run(r.warm(qs, lambda x: gemini.embed(x, s)))
        print(f"{r.mode}:          ", evaluate(r))


if __name__ == "__main__":
    main()
