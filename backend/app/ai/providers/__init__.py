"""Provider 实现集合。

- :class:`FakeProvider`：默认离线 Provider，本地规则返回固定结构；
  CI / 测试环境使用，零网络依赖。
- :class:`OpenAICompatibleProvider`：OpenAI 兼容 HTTP 协议（Qwen / DeepSeek / Zhipu
  均可走 OpenAI 协议），仅做最薄封装，便于以后接入更多模型。
- :class:`OfflineProvider`：所有可用 Provider 不可用时的兜底，
  返回带 ``offline_used`` 标记的结构，业务可继续但需在 UI 显式提示。
"""

from __future__ import annotations

from app.ai.providers.base import AIProvider, GenerationRequest, GenerationResponse, SyncAIProvider
from app.ai.providers.fake import FakeProvider, build_fake_provider
from app.ai.providers.offline import OfflineProvider, build_offline_provider
from app.ai.providers.openai_compatible import (
    OpenAICompatibleProvider,
    build_openai_compatible_provider,
)

__all__ = [
    "AIProvider",
    "FakeProvider",
    "GenerationRequest",
    "GenerationResponse",
    "OfflineProvider",
    "OpenAICompatibleProvider",
    "SyncAIProvider",
    "build_fake_provider",
    "build_offline_provider",
    "build_openai_compatible_provider",
]
