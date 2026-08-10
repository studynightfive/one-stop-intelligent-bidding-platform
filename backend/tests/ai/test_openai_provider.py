"""OpenAI 兼容 Provider 测试。"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.ai.errors import (
    AIServiceUnavailable,
    ProviderError,
    ProviderRateLimited,
    ProviderTimeout,
)
from app.ai.providers.base import GenerationRequest
from app.ai.providers.openai_compatible import (
    OpenAICompatibleProvider,
    ProviderSettings,
    _extract_status_error,
    _usage_from_payload,
    build_openai_compatible_provider,
)


def _req() -> GenerationRequest:
    return GenerationRequest(
        prompt_name="tender_parse",
        prompt_version="1.0.0",
        model="qwen-plus",
        system_prompt="system",
        user_prompt="user",
    )


def _settings(**overrides: Any) -> ProviderSettings:
    base = dict(
        name="qwen",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="test-key",
        default_model="qwen-plus",
    )
    base.update(overrides)
    return ProviderSettings(**base)


@pytest.mark.asyncio
async def test_provider_disabled_raises_unavailable() -> None:
    p = OpenAICompatibleProvider(_settings(enabled=False))
    with pytest.raises(AIServiceUnavailable):
        await p.generate(_req())


@pytest.mark.asyncio
async def test_provider_is_available_requires_key() -> None:
    p = OpenAICompatibleProvider(_settings(api_key=""))
    assert p.is_available() is False


def test_provider_factory_uses_settings() -> None:
    p = build_openai_compatible_provider(
        name="qwen",
        base_url="https://example.com/v1",
        api_key="test",
        default_model="qwen-plus",
    )
    assert p.is_available() is True
    assert p.name == "qwen"


def test_extract_status_error_classifies_status() -> None:
    response_429 = httpx.Response(429, text="rate limited", request=httpx.Request("POST", "https://example.com"))
    assert isinstance(_extract_status_error(response_429), ProviderRateLimited)
    response_401 = httpx.Response(401, text="unauth", request=httpx.Request("POST", "https://example.com"))
    assert isinstance(_extract_status_error(response_401), AIServiceUnavailable)
    response_504 = httpx.Response(504, text="timeout", request=httpx.Request("POST", "https://example.com"))
    assert isinstance(_extract_status_error(response_504), ProviderTimeout)
    response_500 = httpx.Response(500, text="oops", request=httpx.Request("POST", "https://example.com"))
    assert isinstance(_extract_status_error(response_500), ProviderError)


def test_usage_from_payload_handles_missing() -> None:
    assert _usage_from_payload(None).total == 0
    usage = _usage_from_payload({"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3})
    assert usage.prompt == 1
    assert usage.completion == 2
    assert usage.total == 3


@pytest.mark.asyncio
async def test_provider_calls_http_and_returns_response() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"k":"v"}'}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12},
            },
        )
    )
    client = httpx.AsyncClient(transport=transport, base_url="https://example.com/v1")
    p = OpenAICompatibleProvider(_settings(), http_client=client)
    response = await p.generate(_req())
    assert response.text.startswith("{")
    assert response.structured == {"k": "v"}
    assert response.token_usage.total == 12


@pytest.mark.asyncio
async def test_provider_retries_on_5xx() -> None:
    attempt = {"n": 0}

    def transport(request: httpx.Request) -> httpx.Response:
        attempt["n"] += 1
        if attempt["n"] == 1:
            return httpx.Response(500, text="server error", request=request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}, request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(transport), base_url="https://example.com/v1")
    p = OpenAICompatibleProvider(_settings(max_retries=2), http_client=client)
    response = await p.generate(_req())
    assert response.text == "ok"
    assert attempt["n"] == 2


@pytest.mark.asyncio
async def test_provider_raises_after_retry_exhausted() -> None:
    def transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="down", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(transport), base_url="https://example.com/v1")
    p = OpenAICompatibleProvider(_settings(max_retries=1), http_client=client)
    with pytest.raises(ProviderError):
        await p.generate(_req())


@pytest.mark.asyncio
async def test_provider_raises_on_http_error() -> None:
    def transport(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns failed")

    client = httpx.AsyncClient(transport=httpx.MockTransport(transport), base_url="https://example.com/v1")
    p = OpenAICompatibleProvider(_settings(max_retries=0), http_client=client)
    with pytest.raises(ProviderError):
        await p.generate(_req())
