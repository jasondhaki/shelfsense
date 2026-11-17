"""Mirror the RAG chunks + embeddings into Postgres with pgvector (Neon free tier supports it).

    uv run python -m scripts.sync_pgvector             # uses DATABASE_URL from .env

The app itself retrieves from the committed index.npz so the demo stays offline (rule 4); this
table is the same index in a real vector database for other consumers (SQL, n8n, notebooks).
Prints the nearest neighbours of one chunk as a check."""

import json

import numpy as np
import psycopg

from app.config import get_settings
from app.rag.retriever import RAG


def main() -> None:
    url = get_settings().database_url
    if not url.startswith("postgres"):
        raise SystemExit("Set DATABASE_URL to a Postgres URL (e.g. Neon) first.")
    chunks = json.loads((RAG / "chunks.json").read_text("utf-8"))
    data = np.load(RAG / "index.npz")
    vecs = dict(zip(data["ids"].tolist(), data["embeddings"], strict=True))
    if not all(c["id"] in vecs for c in chunks):
        raise SystemExit("index.npz is stale: run scripts.build_rag_index --vector first.")
    dim = data["embeddings"].shape[1]
    with psycopg.connect(url) as db:
        db.execute("CREATE EXTENSION IF NOT EXISTS vector")
        db.execute(
            f"""CREATE TABLE IF NOT EXISTS rag_chunks (
                id text PRIMARY KEY, source text, title text, url text, sku_ids text[],
                context text, text text, embedding vector({dim}))"""
        )
        with db.cursor() as cur:
            cur.executemany(
                """INSERT INTO rag_chunks VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector)
                ON CONFLICT (id) DO UPDATE SET source=EXCLUDED.source, title=EXCLUDED.title,
                url=EXCLUDED.url, sku_ids=EXCLUDED.sku_ids, context=EXCLUDED.context,
                text=EXCLUDED.text, embedding=EXCLUDED.embedding""",
                [
                    (
                        c["id"],
                        c["source"],
                        c["title"],
                        c.get("url", ""),
                        c["sku_ids"],
                        c["context"],
                        c["text"],
                        str(vecs[c["id"]].tolist()),
                    )
                    for c in chunks
                ],
            )
        db.execute("DELETE FROM rag_chunks WHERE id <> ALL(%s)", ([c["id"] for c in chunks],))
        rows = db.execute(
            """SELECT id, round((1 - (embedding <=> (SELECT embedding FROM rag_chunks
               WHERE id = 'foodkeeper_STRW-01#0')))::numeric, 3) FROM rag_chunks
               ORDER BY embedding <=> (SELECT embedding FROM rag_chunks
               WHERE id = 'foodkeeper_STRW-01#0') LIMIT 4"""
        ).fetchall()
    print(f"  upserted {len(chunks)} chunks ({dim}-d) into rag_chunks")
    print("  nearest to foodkeeper_STRW-01#0:", rows)


if __name__ == "__main__":
    main()
