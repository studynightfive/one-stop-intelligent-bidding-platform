"""离线兜底 Provider。

当主 Provider 与 fallback 全部失败时使用，
返回明确的 ``offline_used`` 标记 + 业务可继续的最小结构。

注意：本 Provider 不抛错（除被熔断打开外），业务可继续推进，
但 UI 必须显式提示用户当前为降级模式，结果可能不完整。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.ai.providers.base import GenerationRequest, GenerationResponse, SyncAIProvider
from app.ai.schemas import ProviderStatus, TokenUsage


def _empty_structured(prompt_name: str) -> dict[str, Any]:
    return {
        "summary": "AI 服务暂不可用，已切换为离线模式，结果可能不完整。",
        "offlineUsed": True,
        "promptName": prompt_name,
        "findings": [],
        "matches": [],
        "outline": [],
        "scores": [],
    }


@dataclass
class OfflineProvider(SyncAIProvider):
    """离线兜底 Provider。永远可用（只要 Python 解释器在）。"""

    name: str = "offline"
    model: str = "offline-v1"

    def is_available(self) -> bool:
        return True

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        structured = _empty_structured(request.prompt_name)
        text = json.dumps(structured, ensure_ascii=False, sort_keys=True)
        return GenerationResponse(
            text=text,
            structured=structured,
            token_usage=TokenUsage(),
            model=self.model,
            provider=self.name,
            latency_ms=0,
            provider_status=ProviderStatus.OFFLINE,
        )


def build_offline_provider(name: str = "offline") -> OfflineProvider:
    return OfflineProvider(name=name)
