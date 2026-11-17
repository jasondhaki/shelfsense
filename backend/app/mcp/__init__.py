"""MCP servers: the simulation and the knowledge base as tools for MCP hosts (Claude Code,
Claude Desktop, n8n's MCP client). Read-only: no tool changes a running session."""

import argparse

from mcp.server.mcpserver import MCPServer


def serve(server: MCPServer, default_port: int) -> None:
    """stdio by default (local hosts); --http for streamable HTTP at /mcp."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--http", action="store_true", help="streamable HTTP instead of stdio")
    ap.add_argument("--port", type=int, default=default_port)
    a = ap.parse_args()
    if a.http:
        server.run("streamable-http", host="127.0.0.1", port=a.port)
    else:
        server.run()
