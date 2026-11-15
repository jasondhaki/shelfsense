"""app.sim must stay pure: no imports from the rest of the app, no web/IO frameworks."""

import ast
from pathlib import Path

SIM = Path(__file__).resolve().parents[1] / "app" / "sim"
FORBIDDEN = (
    "app.agents",
    "app.services",
    "app.api",
    "app.controller",
    "app.models",
    "app.rag",
    "app.main",
    "app.config",
    "fastapi",
    "httpx",
    "asyncio",
    "random",
)


def test_sim_imports_are_pure():
    bad = []
    for f in SIM.glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            bad += [
                f"{f.name}: {n}"
                for n in names
                if any(n == p or n.startswith(p + ".") for p in FORBIDDEN)
            ]
    assert not bad, bad
