"""MCP server `shelfsense-vision`: grade shelf photos the way VISION_AGENT does (AI_PIPELINE §1).

uv run python -m app.mcp.vision_server            # stdio
uv run python -m app.mcp.vision_server --http     # streamable HTTP, http://127.0.0.1:8767/mcp

Preset frames use the reviewed cached fixtures (offline). Local photos need live Gemini
(VISION_MODE-independent: GEMINI_API_KEY + GEMINI_VISION_MODEL). Nothing is applied to a session.
"""

import asyncio
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from app.agents.vision_agent import FIXTURES, LABEL_TO_SKU, fixture
from app.config import get_settings
from app.mcp import serve
from app.models.contracts import VisionExtraction
from app.services import gemini
from app.sim.shelf_life import alpha_from_vision

server = MCPServer(
    "shelfsense-vision",
    instructions="Grades produce photos into structured JSON (label, quality 1-10, defects) and "
    "the shelf-life acceleration α ShelfSense would apply. α is plain Python, not the LLM.",
)
MIME = {b"\xff\xd8\xff": "image/jpeg", b"\x89PNG": "image/png"}


def _graded(x: VisionExtraction, source: str) -> dict:
    return {
        "source": source,
        "extraction": x.model_dump(),
        "sku_id": LABEL_TO_SKU.get(x.primary_sku_label),
        "alpha_vision": round(alpha_from_vision(x.visual_quality_score, x.defects_detected), 3),
    }


@server.tool()
def list_frames() -> list[dict]:
    """The preset demo frames with their cached labels."""
    return [
        {"frame_id": p.stem, "label": fixture(p.stem).primary_sku_label}
        for p in sorted(FIXTURES.glob("frame?.json"))
    ]


@server.tool()
def grade_frame(frame_id: str) -> dict:
    """Cached, reviewed grading of a preset frame (frame1..frame3) and its α."""
    if not (FIXTURES / f"{frame_id}.json").is_file():
        raise ValueError(f"Unknown frame {frame_id}; call list_frames.")
    return _graded(fixture(frame_id), "fixture")


@server.tool()
def grade_image(path: str) -> dict:
    """Live Gemini grading of a local JPEG/PNG (≤ 5 MB) and its α."""
    s = get_settings()
    if not gemini.live_ready(s):
        raise ValueError("Live vision needs GEMINI_API_KEY and GEMINI_VISION_MODEL in .env.")
    data = Path(path).read_bytes()
    mime = next((m for sig, m in MIME.items() if data.startswith(sig)), None)
    if mime is None or len(data) > 5 * 1024 * 1024:
        raise ValueError("Send a JPEG or PNG of at most 5 MB.")
    x = asyncio.run(gemini.extract(data, mime, s))
    if x is None:
        raise ValueError("The vision model couldn't read this image.")
    return _graded(x, "gemini")


if __name__ == "__main__":
    serve(server, 8767)
