"""Provider 工厂。

按场景组装 ``primary → fallback → offline`` 三段路由，
``AI_FAKE_PROVIDER=true``（默认）时全部走 Fake，便于本地/CI/Phase 0 启动。
生产环境由运维在 settings 表写入 ModelProvider + ModelRoute 后调用。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.providers.base import AIProvider, SyncAIProvider
from app.ai.providers.fake import build_fake_provider
from app.ai.providers.offline import build_offline_provider
from app.ai.providers.openai_compatible import build_openai_compatible_provider
from app.ai.settings import AISettings

Provider = AIProvider | SyncAIProvider


@dataclass(frozen=True)
class RouteDefinition:
    """路由声明（场景 → 主 / 备 / 模型）。"""

    scene: str
    primary_provider: str
    primary_model: str
    fallback_provider: str | None = None
    fallback_model: str | None = None


@dataclass(frozen=True)
class ProviderRegistry:
    """Provider 注册表。"""

    providers: dict[str, Provider] = field(default_factory=dict)

    def register(self, provider: Provider) -> None:
        self.providers[provider.name] = provider

    def get(self, name: str) -> Provider | None:
        return self.providers.get(name)

    def names(self) -> list[str]:
        return list(self.providers.keys())


def build_default_registry(settings: AISettings) -> ProviderRegistry:
    """构造默认注册表。

    当 ``AI_FAKE_PROVIDER=true``（默认）时加入 fake + offline；
    当 ``AI_FAKE_PROVIDER=false`` 时仅加入 offline（生产环境由
    M4 ``SettingsService`` 注入真实 Provider 后替换）。
    """

    registry = ProviderRegistry()
    if settings.fake_provider:
        registry.register(build_fake_provider(name="fake"))
    else:
        registry.register(
            build_openai_compatible_provider(
                name=settings.default_provider,
                base_url="",
                api_key="",
                default_model="qwen-plus",
                enabled=False,
                timeout_seconds=settings.request_timeout_seconds,
                max_retries=settings.max_retries,
            )
        )
    registry.register(build_offline_provider())
    return registry


__all__ = [
    "Provider",
    "ProviderRegistry",
    "RouteDefinition",
    "build_default_registry",
]
