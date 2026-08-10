"""M7 AI 配置。

仅读取环境变量，不直接 import 平台配置。
默认离线（fake provider），与 ``.env.example`` 中 ``AI_FAKE_PROVIDER=true`` 一致，
便于 CI 跑回归和 Phase 0 启动。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class AISettings:
    """AI 抽象层运行时配置。"""

    fake_provider: bool
    default_provider: str
    request_timeout_seconds: float
    max_retries: int
    circuit_breaker_failures: int
    circuit_breaker_cooldown_seconds: float
    redis_url: str | None
    cache_ttl_seconds: int
    master_key_path: str | None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> AISettings:
        mapping: Mapping[str, str] = env if env is not None else os.environ
        return cls(
            fake_provider=_get_bool("AI_FAKE_PROVIDER", default=True),
            default_provider=mapping.get("AI_DEFAULT_PROVIDER", "qwen").strip() or "qwen",
            request_timeout_seconds=float(mapping.get("AI_REQUEST_TIMEOUT_SECONDS", "60") or 60),
            max_retries=_get_int("AI_MAX_RETRIES", 3),
            circuit_breaker_failures=_get_int("AI_CIRCUIT_BREAKER_FAILURES", 3),
            circuit_breaker_cooldown_seconds=float(mapping.get("AI_CIRCUIT_BREAKER_COOLDOWN_SECONDS", "600") or 600),
            redis_url=mapping.get("REDIS_URL") or None,
            cache_ttl_seconds=_get_int("AI_CACHE_TTL_SECONDS", 300),
            master_key_path=mapping.get("MODEL_MASTER_KEY_PATH") or None,
        )


def get_settings() -> AISettings:
    """延迟读取环境变量，便于测试覆盖。"""
    return AISettings.from_env()
