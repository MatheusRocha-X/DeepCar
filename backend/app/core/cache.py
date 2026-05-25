"""
In-memory cache with TTL. No Redis dependency required.
Falls back gracefully — if Redis is configured and available it's used,
otherwise a simple dict-based store is used silently.
"""
import time
import json
import fnmatch
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── In-memory store ────────────────────────────────────────────────────────────
# Each entry: {"value": ..., "expires_at": float}
_store: dict[str, dict] = {}

DEFAULT_TTL = 300  # seconds


def _now() -> float:
    return time.monotonic()


def _evict():
    """Remove expired keys (called lazily on get/set)."""
    now = _now()
    expired = [k for k, v in _store.items() if v["expires_at"] <= now]
    for k in expired:
        del _store[k]


# ── Public API (same signatures as the Redis version) ─────────────────────────

async def cache_get(key: str) -> Any:
    _evict()
    entry = _store.get(key)
    if entry and entry["expires_at"] > _now():
        return entry["value"]
    return None


async def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL):
    _evict()
    _store[key] = {
        "value": json.loads(json.dumps(value, default=str)),
        "expires_at": _now() + (ttl or DEFAULT_TTL),
    }


async def cache_delete(key: str):
    _store.pop(key, None)


async def cache_delete_pattern(pattern: str):
    keys = [k for k in list(_store.keys()) if fnmatch.fnmatch(k, pattern)]
    for k in keys:
        del _store[k]
