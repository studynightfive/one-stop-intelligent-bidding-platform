"""Worker 配置。

仅读取环境变量，不直接 import 平台 SettingsService。
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
class WorkerSettings:
    """Celery Worker 配置。"""

    broker_url: str
    result_backend: str
    key_prefix: str
    task_default_queue: str
    task_acks_late: bool
    task_reject_on_worker_lost: bool
    worker_max_tasks_per_child: int
    worker_prefetch_multiplier: int
    task_soft_time_limit_seconds: int
    task_hard_time_limit_seconds: int
    visibility_timeout_seconds: int
    eager_mode: bool

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> WorkerSettings:
        mapping: Mapping[str, str] = env if env is not None else os.environ
        broker = mapping.get("REDIS_URL", "redis://redis:6379/1")
        key_prefix = mapping.get("REDIS_KEY_PREFIX", "bidplat:development")
        return cls(
            broker_url=broker,
            result_backend=broker,
            key_prefix=key_prefix,
            task_default_queue=mapping.get("WORKER_DEFAULT_QUEUE", "m7_workers"),
            task_acks_late=_get_bool("WORKER_ACKS_LATE", default=True),
            task_reject_on_worker_lost=_get_bool("WORKER_REJECT_ON_LOST", default=True),
            worker_max_tasks_per_child=_get_int("WORKER_MAX_TASKS_PER_CHILD", 200),
            worker_prefetch_multiplier=_get_int("WORKER_PREFETCH_MULTIPLIER", 1),
            task_soft_time_limit_seconds=_get_int("WORKER_SOFT_TIME_LIMIT", 240),
            task_hard_time_limit_seconds=_get_int("WORKER_HARD_TIME_LIMIT", 300),
            visibility_timeout_seconds=_get_int("WORKER_VISIBILITY_TIMEOUT", 900),
            eager_mode=_get_bool("WORKER_EAGER_MODE", default=False),
        )


def get_worker_settings() -> WorkerSettings:
    """延迟读取环境变量，便于测试覆盖。"""

    return WorkerSettings.from_env()
