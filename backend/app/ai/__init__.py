"""M7 AI 抽象层。

本包提供 LangGraph 状态机、模型路由、提示词版本管理和 Provider 适配。
业务模块（M5 投标 / M6 评标）通过 Celery Worker 间接调用本层，
本层不直接 import M5/M6 业务表或 ORM。

公开入口：
- :func:`app.ai.router.invoke`：模型路由（primary → fallback → offline）。
- :func:`app.ai.prompts.registry.load_prompt`：按版本读取提示词模板。
- :class:`app.ai.schemas.JobSpec` / :class:`app.ai.schemas.JobResult`：Worker 任务入参与返回契约。
"""

from __future__ import annotations

from typing import Any

from app.ai.errors import (
    AIInvocationError,
    AIServiceUnavailable,
    AllProvidersFailed,
    CircuitOpen,
    ProviderError,
    ProviderRateLimited,
    ProviderTimeout,
)
from app.ai.schemas import (
    JobResult,
    JobSpec,
    JobStatus,
    PromptVersion,
    ProviderStatus,
    Scene,
    TokenUsage,
    hash_payload,
)

__all__ = [
    "AIServiceUnavailable",
    "AIInvocationError",
    "AllProvidersFailed",
    "CircuitOpen",
    "JobResult",
    "JobSpec",
    "JobStatus",
    "ProviderError",
    "ProviderRateLimited",
    "ProviderStatus",
    "PromptVersion",
    "ProviderTimeout",
    "Scene",
    "TokenUsage",
    "hash_payload",
]


def __getattr__(name: str) -> Any:
    """延迟导入 router 与 prompts，避免初始化时的循环依赖。"""

    if name in {"ModelRouter", "invoke", "get_router", "reset_router_for_tests", "RouteConfig", "RouterOptions"}:
        from app.ai import router as _router

        return getattr(_router, name)
    if name in {"load_prompt", "PromptTemplate", "PromptRegistry", "build_default_registry", "PromptFactory"}:
        from app.ai.prompts import registry as _registry

        return getattr(_registry, name)
    raise AttributeError(name)
