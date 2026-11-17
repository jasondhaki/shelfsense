"""Text generation for plain-language explanations (AI_PIPELINE §3).

Providers: Gemini (free tier, `GEMINI_TEXT_MODEL`) or a local open-weight model served by
Ollama (`OLLAMA_MODEL`, e.g. qwen2.5:3b). Temperature 0, capped output. Never raises: returns
None and the caller falls back to template text (hard rule 4)."""

import asyncio
import logging

import httpx

from app.config import Settings

log = logging.getLogger(__name__)


def target(s: Settings) -> tuple[str, str] | None:
    """(provider, model) when a text model is configured, else None."""
    if s.llm_provider == "gemini":
        model = s.gemini_text_model or s.gemini_vision_model
        return ("gemini", model) if s.gemini_api_key and model else None
    if s.llm_provider == "ollama" and s.ollama_model:
        return ("ollama", s.ollama_model)
    return None


async def generate(system: str, user: str, s: Settings, max_tokens: int = 300) -> str | None:
    t = target(s)
    if t is None:
        return None
    provider, model = t
    try:
        if provider == "ollama":
            async with httpx.AsyncClient(timeout=s.llm_timeout_s) as c:
                r = await c.post(
                    f"{s.ollama_url.rstrip('/')}/api/chat",
                    json={
                        "model": model,
                        "stream": False,
                        "options": {"temperature": 0, "num_predict": max_tokens},
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    },
                )
                r.raise_for_status()
                return (r.json().get("message", {}).get("content") or "").strip() or None
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=s.gemini_api_key)
        resp = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=model,
                contents=user,
                # thinking models spend output tokens before answering: leave them room
                config=types.GenerateContentConfig(
                    system_instruction=system, temperature=0, max_output_tokens=max_tokens * 4
                ),
            ),
            timeout=s.llm_timeout_s,
        )
        return (resp.text or "").strip() or None
    except Exception as e:  # network, quota, model not pulled: the template answers instead
        log.warning("LLM (%s %s) failed: %s: %s", provider, model, type(e).__name__, e)
        return None
