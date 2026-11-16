"""Gemini multimodal extraction (AI_PIPELINE §1). Structured JSON output, temperature 0,
timeout + 1 retry, schema validation. Never raises: returns None and lets the caller fall back.
Model names come from env (GEMINI_VISION_MODEL) — never hard-coded."""

import asyncio
import logging
from pathlib import Path

from pydantic import ValidationError

from app.config import Settings
from app.models.contracts import VisionExtraction

log = logging.getLogger(__name__)
PROMPT = (Path(__file__).resolve().parents[1] / "agents" / "prompts" / "vision.txt").read_text(
    encoding="utf-8"
)


def live_ready(s: Settings) -> bool:
    return bool(s.gemini_api_key and s.gemini_vision_model)


async def extract(image: bytes, mime: str, s: Settings) -> VisionExtraction | None:
    if not live_ready(s):
        return None
    try:
        from google import genai
        from google.genai import types
    except ImportError:  # pragma: no cover - dependency is declared
        log.warning("google-genai not installed")
        return None

    client = genai.Client(api_key=s.gemini_api_key)
    config = types.GenerateContentConfig(
        temperature=0,
        response_mime_type="application/json",
        response_schema=VisionExtraction,
    )
    contents = [PROMPT, types.Part.from_bytes(data=image, mime_type=mime)]
    for attempt in range(2):  # first try + 1 retry (not after a timeout: slow + spends quota)
        try:
            resp = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=s.gemini_vision_model, contents=contents, config=config
                ),
                timeout=s.vision_timeout_s,
            )
            return VisionExtraction.model_validate_json(resp.text or "")
        except TimeoutError:
            log.warning("Gemini vision timed out after %.0fs", s.vision_timeout_s)
            return None
        except (ValidationError, ValueError) as e:
            log.warning("Gemini vision attempt %d: invalid reply: %s", attempt + 1, e)
        except Exception as e:  # SDK/network errors: never let them reach the sim loop
            log.warning("Gemini vision attempt %d error: %s: %s", attempt + 1, type(e).__name__, e)
            if _client_error(e):
                return None  # 4xx (bad model, auth, quota): retrying can't help
    return None


async def embed(texts: list[str], s: Settings):
    """Batched, L2-normalised embeddings as a float32 matrix, or None (never raises)."""
    if not (s.gemini_api_key and s.gemini_embed_model) or not texts:
        return None
    import numpy as np
    from google import genai

    client = genai.Client(api_key=s.gemini_api_key)
    for attempt in range(2):
        try:
            resp = await asyncio.wait_for(
                client.aio.models.embed_content(model=s.gemini_embed_model, contents=texts),
                timeout=max(s.http_timeout_s, 30),
            )
            m = np.array([e.values for e in resp.embeddings], dtype="float32")
            return m / np.linalg.norm(m, axis=1, keepdims=True).clip(min=1e-9)
        except Exception as e:  # never break callers
            log.warning("Gemini embed attempt %d failed: %s: %s", attempt + 1, type(e).__name__, e)
            if _client_error(e):
                return None
    return None


def _client_error(e: Exception) -> bool:
    code = getattr(e, "code", None)
    return isinstance(code, int) and 400 <= code < 500
