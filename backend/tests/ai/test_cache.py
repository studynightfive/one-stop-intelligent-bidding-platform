"""AI 缓存测试。"""

from __future__ import annotations

import time

import pytest

from app.ai.cache import InMemoryCache, cache_key, response_from_cache_payload, response_to_cache_payload
from app.ai.providers.base import GenerationResponse
from app.ai.schemas import TokenUsage


@pytest.mark.asyncio
async def test_inmemory_cache_round_trip() -> None:
    cache = InMemoryCache()
    await cache.set("k", {"a": 1, "b": "two"}, ttl_seconds=60)
    assert await cache.get("k") == {"a": 1, "b": "two"}


@pytest.mark.asyncio
async def test_inmemory_cache_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = InMemoryCache()
    await cache.set("k", {"x": 1}, ttl_seconds=1)
    assert await cache.get("k") is not None
    base_time = time.time()
    monkeypatch.setattr("app.ai.cache.time.time", lambda: base_time + 100)
    assert await cache.get("k") is None


def test_cache_key_includes_all_dimensions() -> None:
    payload = {"a": 1}
    k1 = cache_key("scene", "model-a", "v1", payload)
    k2 = cache_key("scene", "model-b", "v1", payload)
    k3 = cache_key("scene", "model-a", "v2", payload)
    assert k1 != k2
    assert k1 != k3


def test_response_payload_round_trip() -> None:
    response = GenerationResponse(
        text="hello",
        structured={"k": "v"},
        token_usage=TokenUsage(prompt=3, completion=5, total=8),
        model="qwen-plus",
        provider="qwen",
        latency_ms=120,
        provider_status="primary",
    )
    payload = response_to_cache_payload(response)
    restored = response_from_cache_payload(payload)
    assert restored.text == response.text
    assert restored.model == response.model
    assert restored.provider == response.provider
    assert restored.token_usage.prompt == 3
    assert restored.token_usage.completion == 5
    assert restored.token_usage.total == 8
