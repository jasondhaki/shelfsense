"""Text generation for plain-language explanations (AI_PIPELINE §3).

Providers: Gemini (free tier, `GEMINI_TEXT_MODEL`), a local open-weight model served by Ollama
(`OLLAMA_MODEL`, e.g. qwen2.5:3b), or any OpenAI-compatible local server such as llama.cpp's
llama-server (`OPENAI_COMPAT_URL`, `OPENAI_COMPAT_MODEL`). Temperature 0, capped output.
Never raises: returns None and the caller falls back to template text (hard rule 4)."""

import asyncio
import logging
import re

import httpx

from app.config import Settings

log = logging.getLogger(__name__)
THINK = re.compile(r"<think>.*?</think>", re.S)  # reasoning models (DeepSeek-R1) think aloud


def _clean(text: str | None) -> str | None:
    out = THINK.sub("", text or "").strip()
    return None if "<think>" in out else out or None  # ran out of tokens mid-thought


def target(s: Settings) -> tuple[str, str] | None:
    """(provider, model) when a text model is configured, else None."""
    if s.llm_provider == "gemini":
        model = s.gemini_text_model or s.gemini_vision_model
        return ("gemini", model) if s.gemini_api_key and model else None
    if s.llm_provider == "ollama" and s.ollama_model:
        return ("ollama", s.ollama_model)
    if s.llm_provider == "openai_compat" and s.openai_compat_model:
        return ("openai_compat", s.openai_compat_model)
    return None


async def generate(system: str, user: str, s: Settings, max_tokens: int = 300) -> str | None:
    t = target(s)
    if t is None:
        return None
    provider, model = t
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    try:
        if provider == "openai_compat":
            async with httpx.AsyncClient(timeout=s.llm_timeout_s) as c:
                r = await c.post(
                    f"{s.openai_compat_url.rstrip('/')}/chat/completions",
                    json={
                        "model": model,
                        "messages": msgs,
                        "temperature": 0,
                        "max_tokens": max_tokens * 4,
                    },
                )
                r.raise_for_status()
                return _clean(r.json()["choices"][0]["message"]["content"])
        if provider == "ollama":
            async with httpx.AsyncClient(timeout=s.llm_timeout_s) as c:
                r = await c.post(
                    f"{s.ollama_url.rstrip('/')}/api/chat",
                    json={
                        "model": model,
                        "stream": False,
                        # reasoning models (DeepSeek-R1) think first: same headroom as Gemini
                        "options": {"temperature": 0, "num_predict": max_tokens * 4},
                        "messages": msgs,
                    },
                )
                r.raise_for_status()
                return _clean(r.json().get("message", {}).get("content"))
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
