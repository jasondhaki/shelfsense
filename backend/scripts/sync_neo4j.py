"""Load the knowledge graph (data/rag/graph.json) into Neo4j over its HTTP Query API.

    NEO4J_URL=https://<id>.databases.neo4j.io NEO4J_USER=neo4j NEO4J_PASSWORD=... \
        uv run python -m scripts.sync_neo4j

Works with a free Neo4j AuraDB instance or a local Neo4j 5 (http://localhost:7474). The app's
graph RAG reads the same graph from the committed JSON, so the demo needs no database (rule 4).
Then try in Neo4j Browser:
    MATCH (p:Sku)-[:CLASHES_WITH]->(s:Sku)<-[:DESCRIBES]-(d:Document) RETURN p, s, d"""

import json
import os
from collections import defaultdict

import httpx

from app.rag.retriever import RAG


def main() -> None:
    url = os.environ.get("NEO4J_URL", "").rstrip("/")
    db = os.environ.get("NEO4J_DATABASE", "neo4j")
    auth = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))
    if not url or not auth[1]:
        raise SystemExit("Set NEO4J_URL and NEO4J_PASSWORD (and NEO4J_USER if not neo4j).")
    g = json.loads((RAG / "graph.json").read_text("utf-8"))

    def run(statement: str, **params) -> dict:
        r = httpx.post(
            f"{url}/db/{db}/query/v2",
            json={"statement": statement, "parameters": params},
            auth=auth,
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()
        if body.get("errors"):
            raise SystemExit(body["errors"])
        return body

    by_type: dict[str, list[dict]] = defaultdict(list)
    for n in g["nodes"]:
        by_type[n["type"]].append({k: v for k, v in n.items() if k != "type"})
    for label, rows in by_type.items():  # labels can't be parameters; they come from our file
        run(f"UNWIND $rows AS r MERGE (n:{label} {{id: r.id}}) SET n += r", rows=rows)
    rels: dict[str, list[dict]] = defaultdict(list)
    for e in g["edges"]:
        rels[e["type"]].append({"a": e["source"], "b": e["target"]})
    for kind, rows in rels.items():
        run(
            f"UNWIND $rows AS r MATCH (a {{id: r.a}}), (b {{id: r.b}}) MERGE (a)-[:{kind}]->(b)",
            rows=rows,
        )
    print(f"  merged {len(g['nodes'])} nodes and {len(g['edges'])} relationships into {url}")


if __name__ == "__main__":
    main()
