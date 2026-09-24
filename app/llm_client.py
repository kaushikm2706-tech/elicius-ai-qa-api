"""
Talks to the actual LLM. This is the piece the assignment cares about
most: timeout handling, retry/fallback logic, and token usage — all
three are explicit /chat requirements.

Plain-English picture: think of this like calling a taxi app. You ask
for a ride (the question). If the first driver (Gemini) doesn't answer
within a few rings, you don't just give up — you try again once or
twice (retry), and if that driver is still unavailable, you call a
second taxi company (Groq) instead (fallback). Only if BOTH companies
fail do you tell the passenger "sorry, no ride available" (a clean
HTTP error instead of a crash).

Both provider functions return the same shape:
    {"answer": str, "prompt_tokens": int, "completion_tokens": int, "provider": str}
so the rest of the app never needs to know which provider actually
answered.
"""
import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger("llm_client")


class LLMError(Exception):
    """Raised when a provider fails after all its retries."""


async def _call_gemini(question: str) -> dict:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    body = {"contents": [{"parts": [{"text": question}]}]}

    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        resp = await client.post(url, json=body)
    resp.raise_for_status()
    data = resp.json()

    answer = data["candidates"][0]["content"]["parts"][0]["text"]
    usage = data.get("usageMetadata", {})
    return {
        "answer": answer,
        "prompt_tokens": usage.get("promptTokenCount", 0),
        "completion_tokens": usage.get("candidatesTokenCount", 0),
        "provider": "gemini",
    }


async def _call_groq(question: str) -> dict:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    body = {
        "model": settings.groq_model,
        "messages": [{"role": "user", "content": question}],
    }

    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        resp = await client.post(url, json=body, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    answer = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {
        "answer": answer,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "provider": "groq",
    }


async def _call_with_retries(provider_fn, question: str, provider_name: str) -> dict:
    """Tries one provider up to (max_retries + 1) times with exponential
    backoff (1s, 2s, 4s, ...) before giving up on it. Exponential backoff
    means: don't hammer a struggling service — wait a little longer each
    time, since a busy server needs breathing room, not a flood of
    instant retries."""
    last_error = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            return await provider_fn(question)
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.TransportError) as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.warning(
                "%s attempt %d/%d failed (%s); retrying in %ss",
                provider_name, attempt + 1, settings.llm_max_retries + 1, exc, wait,
            )
            if attempt < settings.llm_max_retries:
                await asyncio.sleep(wait)
    raise LLMError(f"{provider_name} failed after retries: {last_error}")


async def get_answer(question: str) -> dict:
    """Primary + fallback entry point used by the /chat endpoint.
    Tries Gemini first; if it's fully exhausted, falls back to Groq.
    Only raises LLMError if BOTH providers are down — that becomes a
    503 in the API layer, never an unhandled crash."""
    try:
        return await _call_with_retries(_call_gemini, question, "gemini")
    except LLMError as gemini_error:
        logger.warning("Falling back to Groq: %s", gemini_error)
        try:
            return await _call_with_retries(_call_groq, question, "groq")
        except LLMError as groq_error:
            raise LLMError(
                f"All providers failed. Gemini: {gemini_error} | Groq: {groq_error}"
            )
