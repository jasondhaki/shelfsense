"""MCP server `shelfsense-warehouse`: read-only SQL over the DuckDB analytics warehouse.

uv run --group seed python -m scripts.export_warehouse      # build it first
uv run --group seed python -m app.mcp.warehouse_server      # stdio (--http: port 8768)

The connection is read-only with external file access disabled, and only one SELECT/WITH
statement is accepted, so a tool call can't write, read other files or reach the network.
"""

import duckdb
from mcp.server.mcpserver import MCPServer

from app.mcp import serve
from scripts.export_warehouse import OUT

DB = OUT / "shelfsense.duckdb"
MAX_ROWS = 200

server = MCPServer(
    "shelfsense-warehouse",
    instructions="DuckDB warehouse of simulated weeks: runs (one row per seed/scenario with KPIs), "
    "daily (waste and revenue per day per store) and sku_waste (wasted units per SKU). "
    "Store A is the baseline, B is ShelfSense. All numbers are simulated.",
)


def _con() -> duckdb.DuckDBPyConnection:
    if not DB.is_file():
        raise ValueError("No warehouse yet: run scripts.export_warehouse first.")
    return duckdb.connect(str(DB), read_only=True, config={"enable_external_access": False})


@server.tool()
def tables() -> dict:
    """Each table's columns and types."""
    with _con() as con:
        rows = con.execute(
            "SELECT table_name, column_name, data_type FROM information_schema.columns "
            "ORDER BY table_name, ordinal_position"
        ).fetchall()
    out: dict[str, dict] = {}
    for t, c, d in rows:
        out.setdefault(t, {})[c] = d
    return out


@server.tool()
def query(sql: str) -> dict:
    """Run one read-only SELECT (or WITH … SELECT); returns up to 200 rows."""
    s = sql.strip().rstrip(";")
    if ";" in s or s.split(None, 1)[0].lower() not in ("select", "with"):
        raise ValueError("Only a single SELECT or WITH statement is allowed.")
    with _con() as con:
        cur = con.execute(s)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(MAX_ROWS + 1)
    return {"columns": cols, "rows": rows[:MAX_ROWS], "truncated": len(rows) > MAX_ROWS}


if __name__ == "__main__":
    serve(server, 8768)
