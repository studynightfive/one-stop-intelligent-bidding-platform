"""AI 调用异常定义。

降级链语义：
- :class:`ProviderError`：单个 Provider 调用失败（5xx / 4xx 业务错误），可继续降级。
- :class:`ProviderRateLimited`：触发限流（429），按 backoff 重试或降级。
- :class:`ProviderTimeout`：调用超时。
- :class:`AIServiceUnavailable`：Provider 主动下线或维护。
- :class:`CircuitOpen`：熔断器打开，路由跳过该 Provider。
- :class:`AllProvidersFailed`：主 + 降级 + 离线 全失败，最终对外异常。
"""

from __future__ import annotations


class AIInvocationError(RuntimeError):
    """AI 调用通用异常基类。"""

    retryable: bool = True

    def __init__(self, message: str, *, provider: str | None = None) -> None:
        super().__init__(message)
        self.provider = provider


class ProviderError(AIInvocationError):
    """Provider 返回 5xx 或业务错误。"""


class ProviderRateLimited(AIInvocationError):
    """Provider 返回 429 或触发限流策略。"""


class ProviderTimeout(AIInvocationError):
    """Provider 调用超时。"""


class AIServiceUnavailable(AIInvocationError):
    """Provider 主动不可用（如维护、配额耗尽）。"""


class CircuitOpen(AIInvocationError):
    """熔断器处于打开状态，路由应跳过该 Provider。"""

    retryable = False


class AllProvidersFailed(AIInvocationError):
    """主 + 降级 + 离线 Provider 全部失败。"""

    retryable = False

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        attempts: list[str] | None = None,
    ) -> None:
        super().__init__(message, provider=provider)
        self.attempts: list[str] = list(attempts or [])
