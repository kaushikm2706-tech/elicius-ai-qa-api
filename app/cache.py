"""
Redis does two jobs here:
  1. Cache: if two users ask the exact same question, the second one
     gets an instant answer instead of paying for another LLM call.
     Think of it as a sticky note on the fridge with yesterday's
     answer already written on it — check the note before cooking again.
  2. Rate limiting: stops one user from firing 1,000 requests a second
     and using up everyone else's LLM quota. Think of it as a bouncer
     with a clicker-counter that resets every minute.

Redis is used for both because it's shared across every FastAPI
instance (see ARCHITECTURE.md) — if each server instance counted
requests only in its own memory, a user could dodge the limit just by
getting load-balanced to a different instance.
"""
import hashlib
import time

import redis

from app.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


def _cache_key(question: str) -> str:
    # Hash the question so cache keys are a fixed, short, safe length
    # regardless of how long the user's question text is.
    digest = hashlib.sha256(question.strip().lower().encode()).hexdigest()
    return f"chat_cache:{digest}"


def get_cached_answer(question: str) -> str | None:
    return redis_client.get(_cache_key(question))


def set_cached_answer(question: str, answer: str) -> None:
    redis_client.setex(_cache_key(question), settings.cache_ttl_seconds, answer)


def is_rate_limited(username: str) -> bool:
    """Fixed-window counter: one key per user per minute. First request
    in a new minute creates the key with a 60s expiry; every request
    after that just increments it. Once the count passes the limit,
    the user is blocked until the window rolls over."""
    window = int(time.time() // 60)
    key = f"rate_limit:{username}:{window}"
    current = redis_client.incr(key)
    if current == 1:
        redis_client.expire(key, 60)
    return current > settings.rate_limit_per_minute
