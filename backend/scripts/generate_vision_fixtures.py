"""Run the three preset frames through live Gemini and save the raw extractions for review.

    uv run python -m scripts.generate_vision_fixtures

Writes data/fixtures/vision/frameN.live.json next to the committed fixtures. Review each one
against the image, hand-correct the story numbers (AI_PIPELINE §1.5: q ≈ 9.2 / 6.4 / 3.8) and
then copy it over frameN.json. Needs GEMINI_API_KEY and GEMINI_VISION_MODEL in .env."""

import asyncio
from pathlib import Path

from app.config import get_settings
from app.services import gemini
from app.sim.shelf_life import alpha_from_vision
from scripts._common import BACKEND, write_json

FRAMES = BACKEND.parent / "frontend" / "public" / "frames"
OUT = BACKEND / "data" / "fixtures" / "vision"


async def main() -> None:
    s = get_settings()
    if not gemini.live_ready(s):
        raise SystemExit("Set GEMINI_API_KEY and GEMINI_VISION_MODEL in D:/shelfsense/.env first.")
    for n in (1, 2, 3):
        img: Path = FRAMES / f"frame{n}.jpg"
        ext = await gemini.extract(img.read_bytes(), "image/jpeg", s)
        if ext is None:
            print(f"frame{n}: no valid response (see warnings above)")
            continue
        write_json(  # save first: never lose a paid call to a console error
            OUT / f"frame{n}.live.json",
            {
                "_note": f"RAW live output from {s.gemini_vision_model}; review before use.",
                **ext.model_dump(),
            },
        )
        a = alpha_from_vision(ext.visual_quality_score, ext.defects_detected)
        print(
            f"frame{n}: q={ext.visual_quality_score} alpha={a:.2f} "
            f"primary={ext.primary_sku_label} defects={ext.defects_detected} "
            f"boxes={len(ext.detections)}"
        )


if __name__ == "__main__":
    asyncio.run(main())
