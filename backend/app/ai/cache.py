"""AI 结果缓存（Redis TTL 5min）。

目的：避免相同输入的 AI 调用浪费配额（短时间重复提交、测试）。
注意：
- 仅缓存「成功」结果；
- Key 含 scene + 模型 + 输入哈希，便于跨模型独立缓存；
- Redis 不可用时缓存层静默退化（不影响路由主流程）。
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from app.ai.schemas import hash_payload

if TYPE_CHECKING:  # pragma: no cover
    from app.ai.providers.base import GenerationResponse

logger = logging.getLogger(__name__)


class InMemoryCache:
    """进程内缓存（测试与未配置 Redis 时使用）。"""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> dict[str, Any] | None:
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, payload = entry
            if expires_at <= time.time():
                self._store.pop(key, None)
                return None
            return payload

    async def set(self, key: str, payload: Mapping[str, Any], ttl_seconds: int) -> None:
        async with self._lock:
            self._store[key] = (time.time() + ttl_seconds, dict(payload))


class RedisCache:
    """Redis 缓存实现。Redis 异常被记录但不影响主流程。"""

    def __init__(self, url: str) -> None:
        import redis.asyncio as redis_asyncio

        self._client = redis_asyncio.from_url(url, encoding="utf-8", decode_responses=True)  # type: ignore[no-untyped-call]

    async def aclose(self) -> None:
        with contextlib.suppress(Exception):  # noqa: BLE001
            await self._client.aclose()

    async def get(self, key: str) -> dict[str, Any] | None:
        try:
            raw = await self._client.get(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ai.cache.get_failed key=%s err=%s", key, exc)
            return None
        if not raw:
            return None
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(loaded, dict):
            return None
        return loaded

    async def set(self, key: str, payload: Mapping[str, Any], ttl_seconds: int) -> None:
        try:
            await self._client.set(
                key,
                json.dumps(payload, ensure_ascii=False, default=str),
                ex=ttl_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("ai.cache.set_failed key=%s err=%s", key, exc)


def build_cache(redis_url: str | None, *, ttl_seconds: int = 300) -> InMemoryCache | RedisCache:
    if redis_url:
        try:
            return RedisCache(redis_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ai.cache.redis_init_failed err=%s; using in-memory", exc)
    return InMemoryCache()


def cache_key(scene: str, model: str, prompt_version: str, payload: Mapping[str, Any] | str | bytes) -> str:
    payload_hash = hash_payload(payload)
    return f"ai:{scene}:{model}:{prompt_version}:{payload_hash}"


def response_to_cache_payload(response: GenerationResponse) -> dict[str, Any]:
    return response.to_dict()


def response_from_cache_payload(payload: Mapping[str, Any]) -> GenerationResponse:
    from app.ai.providers.base import GenerationResponse
    from app.ai.schemas import TokenUsage

    usage_payload = payload.get("tokenUsage") or {}
    return GenerationResponse(
        text=str(payload.get("text", "")),
        structured=payload.get("structured"),
        token_usage=TokenUsage.from_mapping(usage_payload),
        model=str(payload.get("model", "")),
        provider=str(payload.get("provider", "")),
        latency_ms=int(payload.get("latencyMs", 0) or 0),
        provider_status=payload.get("providerStatus", "primary"),
    )
