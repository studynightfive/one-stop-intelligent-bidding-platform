"""Redis 缓存测试（使用 fake redis）。"""

from __future__ import annotations

from typing import Any

import pytest

from app.ai.cache import RedisCache


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._expiry: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value
        if ex is not None:
            self._expiry[key] = ex

    async def aclose(self) -> None:
        pass


def _patch_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()

    def _factory(*args: Any, **kwargs: Any) -> _FakeRedis:
        return fake

    monkeypatch.setattr("redis.asyncio.from_url", _factory)


@pytest.mark.asyncio
async def test_redis_cache_set_and_get(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_redis(monkeypatch)
    cache = RedisCache("redis://localhost:6379/0")
    await cache.set("k", {"a": 1}, ttl_seconds=60)
    assert await cache.get("k") == {"a": 1}


@pytest.mark.asyncio
async def test_redis_cache_handles_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_redis(monkeypatch)
    cache = RedisCache("redis://localhost:6379/0")
    assert await cache.get("missing") is None


@pytest.mark.asyncio
async def test_redis_cache_set_failure_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_redis(monkeypatch)

    class BrokenRedis:
        async def set(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("redis down")

        async def get(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("redis down")

        async def aclose(self) -> None:
            pass

    monkeypatch.setattr("redis.asyncio.from_url", lambda *a, **kw: BrokenRedis())
    cache = RedisCache("redis://localhost:6379/0")
    await cache.set("k", {"a": 1}, ttl_seconds=60)  # 不抛错
    assert await cache.get("k") is None  # 返回 None


@pytest.mark.asyncio
async def test_redis_cache_aclose_swallows_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_redis(monkeypatch)
    cache = RedisCache("redis://localhost:6379/0")
    await cache.aclose()  # 不抛错
