"""Retrieval over data/rag/chunks.json (AI_PIPELINE §2.3).

Modes: bm25 (always available, offline) or vector (Gemini embeddings in data/rag/index.npz).
Vector mode never calls the network inside a tick: query embeddings are pre-computed for the
templated queries at startup (`warm`), and any uncached query falls back to BM25."""

import json
import math
import re
from collections import Counter
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

import numpy as np

RAG = Path(__file__).resolve().parents[2] / "data" / "rag"
TOKEN = re.compile(r"[a-z0-9]+")
STOP = {
    "a",
    "an",
    "and",
    "the",
    "of",
    "to",
    "in",
    "for",
    "is",
    "it",
    "on",
    "or",
    "with",
    "be",
    "as",
    "at",
    "by",
    "are",
    "from",
    "this",
    "that",
    "its",
    "here",
    "can",
    "up",
    "s",
}
K1, B = 1.5, 0.75


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP]


@dataclass(frozen=True)
class Hit:
    chunk_id: str
    source: str
    title: str
    url: str
    sku_ids: tuple[str, ...]
    text: str
    score: float
    mode: str  # bm25 | vector

    def as_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "text": self.text,
            "score": round(self.score, 3),
            "mode": self.mode,
        }


class Retriever:
    def __init__(
        self,
        rag_mode: str = "bm25",
        vector_ready: bool = False,
        rag_dir: Path = RAG,
        embed_model: str = "",
    ) -> None:
        self.rag_dir = rag_dir
        self.embed_model = embed_model
        self.chunks: list[dict] = json.loads((rag_dir / "chunks.json").read_text("utf-8"))
        toks = json.loads((rag_dir / "bm25.json").read_text("utf-8"))
        self.tf = [Counter(toks[c["id"]]) for c in self.chunks]
        self.dl = [sum(t.values()) for t in self.tf]
        self.avgdl = sum(self.dl) / max(len(self.dl), 1)
        df = Counter(t for tf in self.tf for t in tf)
        n = len(self.chunks)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
        self.vectors: np.ndarray | None = None
        npz = rag_dir / "index.npz"
        if npz.exists():
            data = np.load(npz)
            order = {cid: i for i, cid in enumerate(data["ids"].tolist())}
            if all(c["id"] in order for c in self.chunks):
                self.vectors = data["embeddings"][[order[c["id"]] for c in self.chunks]]
        self.query_vecs: dict[str, np.ndarray] = {}
        cache = rag_dir / "query_cache.npz"  # committed: deployed servers warm with zero calls
        if cache.exists():
            c = np.load(cache)
            if str(c["model"]) == embed_model:
                self.query_vecs = dict(zip(c["queries"].tolist(), c["vecs"], strict=True))
        want_vector = rag_mode == "vector" or (rag_mode == "auto" and vector_ready)
        self.mode = "vector" if want_vector and self.vectors is not None else "bm25"
        g = rag_dir / "graph.json"
        graph = json.loads(g.read_text("utf-8")) if g.exists() else {"nodes": [], "edges": []}
        self.nodes: dict[str, dict] = {n["id"]: n for n in graph["nodes"]}
        self.edges: list[dict] = graph["edges"]

    def neighbours(self, node: str, kind: str) -> list[str]:
        """Graph neighbours over `kind` edges, either direction."""
        return [
            e["target"] if e["source"] == node else e["source"]
            for e in self.edges
            if e["type"] == kind and node in (e["source"], e["target"])
        ]

    def graph_facts(self, sku_id: str) -> list[str]:
        """Short facts about a SKU read off the knowledge graph (graph RAG context)."""
        n = self.nodes.get(f"sku:{sku_id}")
        if n is None:
            return []
        name = lambda i: self.nodes[i]["name"]  # noqa: E731
        facts = [
            f"{n['name']} ({sku_id}) is in category {n['category']}; nominal shelf life "
            f"{n['shelf_life_hours']:g} h."
        ]
        clash = self.neighbours(f"sku:{sku_id}", "CLASHES_WITH")
        if n["ethylene"] != "neutral":
            tail = f"; keep apart from {', '.join(map(name, clash))}" if clash else ""
            facts.append(f"{n['name']} is ethylene-{n['ethylene']}{tail}.")
        docs = self.neighbours(f"sku:{sku_id}", "DESCRIBES")
        srcs = sorted({name(s) for d in docs for s in self.neighbours(d, "PUBLISHED_BY")})
        if srcs:
            facts.append(f"{len(docs)} documents describe it, from: {', '.join(srcs)}.")
        return facts

    def graph_retrieve(self, query: str, sku_id: str | None, k: int = 3) -> list[Hit]:
        """Retrieve for the SKU, then follow CLASHES_WITH edges and add the best ethylene
        chunk of each clashing product (multi-hop context plain retrieval misses)."""
        hits = self.retrieve(query, sku_id, k)
        if sku_id:
            seen = {h.chunk_id for h in hits}
            for nb in self.neighbours(f"sku:{sku_id}", "CLASHES_WITH"):
                for h in self.retrieve(f"ethylene {query}", nb.removeprefix("sku:"), 1):
                    if h.chunk_id not in seen:
                        hits.append(h)
                        seen.add(h.chunk_id)
        return hits

    async def warm(self, queries: list[str], embed) -> None:
        """Embed the templated queries once (one batched call). `embed` is gemini.embed-like."""
        if self.mode != "vector":
            return
        todo = [q for q in dict.fromkeys(queries) if q not in self.query_vecs]
        if not todo:
            return
        vecs = await embed(todo)
        if vecs is None:
            self.mode = "bm25"  # degrade, never break
            return
        self.query_vecs.update(zip(todo, vecs, strict=True))
        try:  # best effort: a read-only disk just means re-embedding next start
            np.savez(
                self.rag_dir / "query_cache.npz",
                model=np.array(self.embed_model),
                queries=np.array(list(self.query_vecs)),
                vecs=np.stack(list(self.query_vecs.values())),
            )
        except OSError:
            pass

    def retrieve(
        self,
        query: str,
        sku_id: str | None = None,
        k: int = 3,
        sources: Collection[str] | None = None,
    ) -> list[Hit]:
        idx = [
            i
            for i, c in enumerate(self.chunks)
            if (sku_id is None or not c["sku_ids"] or sku_id in c["sku_ids"])
            and (sources is None or c["source"] in sources)
        ]
        if self.mode == "vector" and query in self.query_vecs and self.vectors is not None:
            sims = self.vectors[idx] @ self.query_vecs[query]
            scored = list(zip(idx, sims.tolist(), strict=True))
            mode = "vector"
        else:
            q = tokenize(query)
            scored = []
            for i in idx:
                tf, s = self.tf[i], 0.0
                for t in q:
                    f = tf.get(t, 0)
                    if f:
                        s += (
                            self.idf[t]
                            * f
                            * (K1 + 1)
                            / (f + K1 * (1 - B + B * self.dl[i] / self.avgdl))
                        )
                scored.append((i, s))
            mode = "bm25"
        scored = [x for x in scored if x[1] > 0]
        scored.sort(key=lambda x: (-x[1], self.chunks[x[0]]["id"]))  # deterministic ties
        return [self._hit(i, s, mode) for i, s in scored[:k]]

    def _hit(self, i: int, score: float, mode: str) -> Hit:
        c = self.chunks[i]
        return Hit(
            c["id"],
            c["source"],
            c["title"],
            c.get("url", ""),
            tuple(c["sku_ids"]),
            c["text"],
            float(score),
            mode,
        )
