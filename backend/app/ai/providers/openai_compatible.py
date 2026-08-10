"""OpenAI 兼容 HTTP Provider。

支持 Qwen / DeepSeek / Zhipu / 自定义 OpenAI 兼容网关。
本 Provider 不直接 import 平台配置，仅通过 :class:`ProviderSettings` 注入，
避免与 M4 SettingsService 重复。

协议参考：``https://platform.openai.com/docs/api-reference/chat``。
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.ai.errors import AIServiceUnavailable, ProviderError, ProviderRateLimited, ProviderTimeout
from app.ai.providers.base import AIProvider, GenerationRequest, GenerationResponse
from app.ai.schemas import ProviderStatus, TokenUsage


@dataclass(frozen=True)
class ProviderSettings:
    """OpenAI 兼容 Provider 配置。"""

    name: str
    base_url: str
    api_key: str
    default_model: str
    timeout_seconds: float = 60.0
    max_retries: int = 2
    enabled: bool = True
    extra_headers: Mapping[str, str] = field(default_factory=dict)


def _extract_status_error(response: httpx.Response) -> Exception:
    status = response.status_code
    text = response.text[:500]
    if status == 429:
        return ProviderRateLimited(f"rate limited: {text}", provider="openai_compatible")
    if status in {401, 403}:
        return AIServiceUnavailable(f"auth failed ({status}): {text}", provider="openai_compatible")
    if status in {408, 504}:
        return ProviderTimeout(f"upstream timeout ({status}): {text}", provider="openai_compatible")
    return ProviderError(f"upstream error {status}: {text}", provider="openai_compatible")


def _usage_from_payload(payload: Mapping[str, Any] | None) -> TokenUsage:
    if not payload:
        return TokenUsage()
    return TokenUsage(
        prompt=int(payload.get("prompt_tokens", 0) or 0),
        completion=int(payload.get("completion_tokens", 0) or 0),
        total=int(payload.get("total_tokens", 0) or 0),
    )


class OpenAICompatibleProvider(AIProvider):
    """薄封装的 OpenAI 协议客户端。"""

    def __init__(
        self,
        settings: ProviderSettings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
            headers={
                "Authorization": f"Bearer {settings.api_key}",
                "Content-Type": "application/json",
                **settings.extra_headers,
            },
        )

    @property  # type: ignore[override]
    def name(self) -> str:
        return self._settings.name

    def is_available(self) -> bool:
        return self._settings.enabled and bool(self._settings.api_key)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self.is_available():
            raise AIServiceUnavailable(f"provider {self.name} disabled", provider=self.name)

        body: dict[str, Any] = {
            "model": request.model or self._settings.default_model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_output_tokens,
        }
        if request.extra:
            body.update(request.extra)

        attempts = max(self._settings.max_retries, 0) + 1
        last_error: Exception | None = None
        started = time.perf_counter()
        for _attempt in range(attempts):
            try:
                response = await self._client.post("/chat/completions", json=body)
            except httpx.TimeoutException as exc:
                last_error = ProviderTimeout(str(exc), provider=self.name)
            except httpx.HTTPError as exc:
                last_error = ProviderError(str(exc), provider=self.name)
            else:
                if response.status_code >= 500:
                    last_error = ProviderError(f"upstream 5xx {response.status_code}", provider=self.name)
                elif response.status_code >= 400:
                    raise _extract_status_error(response) from None
                else:
                    data = response.json()
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    return _build_response(data, request, self._settings.name, elapsed_ms)
        assert last_error is not None
        raise last_error


def _build_response(
    data: dict[str, Any],
    request: GenerationRequest,
    provider_name: str,
    latency_ms: int,
) -> GenerationResponse:
    choices = data.get("choices") or []
    text = ""
    if choices:
        message = choices[0].get("message") or {}
        text = message.get("content") or ""
    structured: dict[str, Any] | None = None
    if text.strip().startswith("{") or text.strip().startswith("["):
        try:
            structured = json.loads(text)
        except json.JSONDecodeError:
            structured = None
    usage = _usage_from_payload(data.get("usage"))
    return GenerationResponse(
        text=text,
        structured=structured,
        token_usage=usage,
        model=request.model,
        provider=provider_name,
        latency_ms=latency_ms,
        provider_status=ProviderStatus.PRIMARY,
    )


def build_openai_compatible_provider(
    *,
    name: str,
    base_url: str,
    api_key: str,
    default_model: str,
    enabled: bool = True,
    timeout_seconds: float = 60.0,
    max_retries: int = 2,
    extra_headers: Mapping[str, str] | None = None,
) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        ProviderSettings(
            name=name,
            base_url=base_url,
            api_key=api_key,
            default_model=default_model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            enabled=enabled,
            extra_headers=dict(extra_headers or {}),
        )
    )
