"""AI Provider 抽象接口。

所有 Provider 必须实现 :class:`AIProvider` 协议，业务层只依赖该协议，
以便在主 Provider / 降级 Provider / 离线 Provider 之间切换。

调用方不应感知 HTTP 客户端细节；超时、重试、限流由 Provider 内部封装。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.ai.schemas import ProviderStatus, TokenUsage


@dataclass(frozen=True)
class GenerationRequest:
    """统一的 Provider 输入负载。"""

    prompt_name: str
    prompt_version: str
    model: str
    system_prompt: str
    user_prompt: str
    temperature: float = 0.2
    top_p: float = 0.9
    max_output_tokens: int = 2048
    timeout_seconds: float = 60.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationResponse:
    """Provider 输出统一格式。"""

    text: str
    structured: dict[str, Any] | None
    token_usage: TokenUsage
    model: str
    provider: str
    latency_ms: int
    provider_status: ProviderStatus | str = ProviderStatus.PRIMARY

    def to_dict(self) -> dict[str, Any]:
        ps = self.provider_status
        status = ps.value if isinstance(ps, ProviderStatus) else ps
        return {
            "text": self.text,
            "structured": self.structured,
            "tokenUsage": self.token_usage.to_dict(),
            "model": self.model,
            "provider": self.provider,
            "latencyMs": self.latency_ms,
            "providerStatus": status,
        }


class AIProvider(Protocol):
    """异步 AI Provider 接口。"""

    name: str

    def is_available(self) -> bool:
        """Provider 是否可用（用于路由过滤）。"""

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """执行一次生成调用，失败抛 :class:`ProviderError` 家族异常。"""


class SyncAIProvider(Protocol):
    """同步 AI Provider 接口（用于 Fake / Offline 简单实现）。"""

    name: str

    def is_available(self) -> bool:
        """Provider 是否可用（用于路由过滤）。"""

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """同步生成调用。"""
