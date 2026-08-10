"""Provider 单元测试。"""

from __future__ import annotations

import json

import pytest

from app.ai.errors import (
    AIServiceUnavailable,
    AllProvidersFailed,
    CircuitOpen,
    ProviderError,
    ProviderRateLimited,
    ProviderTimeout,
)
from app.ai.providers.base import GenerationRequest
from app.ai.providers.fake import FakeProvider
from app.ai.providers.offline import OfflineProvider
from app.ai.providers.openai_compatible import OpenAICompatibleProvider, ProviderSettings
from app.ai.schemas import ProviderStatus


def _req(prompt_name: str = "tender_parse") -> GenerationRequest:
    return GenerationRequest(
        prompt_name=prompt_name,
        prompt_version="1.0.0",
        model="qwen-plus",
        system_prompt="system",
        user_prompt="user",
    )


def test_fake_provider_returns_structured() -> None:
    fake = FakeProvider()
    resp = fake.generate(_req())
    assert resp.provider == "fake"
    assert resp.provider_status == ProviderStatus.OFFLINE
    assert resp.structured is not None
    assert resp.token_usage.total >= 0


def test_fake_provider_handles_unknown_prompt() -> None:
    fake = FakeProvider()
    resp = fake.generate(_req(prompt_name="unknown_scene"))
    assert resp.provider == "fake"
    assert resp.structured is not None
    assert "echo" in resp.structured


def test_offline_provider_always_available() -> None:
    off = OfflineProvider()
    assert off.is_available() is True
    resp = off.generate(_req())
    assert resp.provider_status == ProviderStatus.OFFLINE
    assert resp.structured is not None
    assert resp.structured.get("offlineUsed") is True


def test_openai_compatible_provider_unavailable_without_key() -> None:
    p = OpenAICompatibleProvider(
        ProviderSettings(
            name="qwen",
            base_url="https://example.com",
            api_key="",
            default_model="qwen-plus",
            enabled=True,
        )
    )
    assert p.is_available() is False


@pytest.mark.asyncio
async def test_openai_compatible_provider_raises_when_disabled() -> None:
    p = OpenAICompatibleProvider(
        ProviderSettings(
            name="qwen",
            base_url="https://example.com",
            api_key="",
            default_model="qwen-plus",
            enabled=False,
        )
    )
    with pytest.raises(AIServiceUnavailable):
        await p.generate(_req())


def test_exceptions_hierarchy() -> None:
    """所有 Provider 异常都继承自 AIInvocationError，且 default retryable。"""

    for cls in (ProviderError, ProviderRateLimited, ProviderTimeout, AIServiceUnavailable):
        exc = cls("test")
        assert isinstance(exc, Exception)
    assert CircuitOpen("test").retryable is False
    assert AllProvidersFailed("test").retryable is False
    assert ProviderRateLimited("test").retryable is True


def test_provider_response_serialization() -> None:
    fake = FakeProvider()
    resp = fake.generate(_req("tender_parse"))
    data = resp.to_dict()
    serialized = json.dumps(data, ensure_ascii=False)
    assert "fake" in serialized
    assert "tokenUsage" in serialized
    assert "providerStatus" in serialized
