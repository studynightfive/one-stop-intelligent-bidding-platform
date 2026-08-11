"""模型路由：主 Provider → fallback → 离线。

核心职责：
- 维护每个 Provider 的熔断器（连续失败 → 跳过一段时间）；
- 维护每个 (scene, prompt) 的主/备 Provider 映射；
- 失败时按顺序降级，并把降级信息写入 ``PromptVersion.status``。

降级原则：永不阻塞业务。返回 ``provider_used=offline`` 时业务可继续，
但需通过 ``M4 AuditService`` 留痕（由 Worker 在 JobResult 上送）。

``ModelRouter`` 是单例模式（``get_router``），Worker 启动时初始化。
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from app.ai.cache import (
    InMemoryCache,
    build_cache,
    cache_key,
    response_from_cache_payload,
    response_to_cache_payload,
)
from app.ai.errors import (
    AIServiceUnavailable,
    AllProvidersFailed,
    CircuitOpen,
    ProviderError,
)
from app.ai.prompts.registry import PromptRegistry, PromptTemplate, load_prompt
from app.ai.providers.base import GenerationRequest, GenerationResponse
from app.ai.providers.factory import Provider, ProviderRegistry, build_default_registry
from app.ai.schemas import (
    JobSpec,
    PromptVersion,
    ProviderOutput,
    ProviderStatus,
    TokenUsage,
    hash_payload,
)
from app.ai.settings import AISettings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class _CircuitState:
    failures: int = 0
    opened_at: float = 0.0

    def is_open(self, threshold: int, cooldown_seconds: float) -> bool:
        if self.failures < threshold:
            return False
        return (time.monotonic() - self.opened_at) < cooldown_seconds


@dataclass
class RouteConfig:
    """场景 → Provider/模型 映射。"""

    scene: str
    prompt_name: str
    primary_provider: str
    primary_model: str
    fallback_provider: str | None = None
    fallback_model: str | None = None


@dataclass(frozen=True)
class RouterOptions:
    """路由运行参数。"""

    use_cache: bool = True
    raise_on_total_failure: bool = False  # 默认 False：业务优先


class ModelRouter:
    """主入口：执行 ``invoke`` 调用。"""

    def __init__(
        self,
        *,
        registry: ProviderRegistry,
        prompts: PromptRegistry,
        settings: AISettings | None = None,
        cache: InMemoryCache | object | None = None,
    ) -> None:
        self.registry = registry
        self.prompts = prompts
        self.settings = settings or get_settings()
        self._cache: Any = cache or build_cache(self.settings.redis_url, ttl_seconds=self.settings.cache_ttl_seconds)
        self._circuits: dict[str, _CircuitState] = {}
        self._route_configs: dict[str, RouteConfig] = {}

    def register_route(self, config: RouteConfig) -> None:
        self._route_configs[config.prompt_name] = config

    def register_default_routes(self) -> None:
        """注册全部默认场景（Phase 1 占位：primary=fake）。"""

        scenes = [
            "tender_parse",
            "requirement_extract",
            "material_match",
            "bid_review",
            "bid_generate",
            "bid_generate_plan",
            "bid_generate_paragraph",
            "risk_check",
            "evaluation_check",
            "evaluation_score",
            "report_generate",
        ]
        for scene in scenes:
            self.register_route(
                RouteConfig(
                    scene=scene,
                    prompt_name=scene,
                    primary_provider="fake",
                    primary_model="qwen-plus",
                    fallback_provider="offline",
                    fallback_model="offline-v1",
                )
            )

    async def invoke(
        self,
        spec: JobSpec,
        *,
        options: RouterOptions | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> ProviderOutput:
        opts = options or RouterOptions()
        template = self._resolve_prompt(spec)
        system_prompt, user_prompt = template.render(payload)
        request_payload = {
            "spec": spec.to_dict(),
            "prompt": payload or {},
        }

        if opts.use_cache:
            cached = await self._cache_lookup(template, request_payload)
            if cached is not None:
                return self._wrap_response(
                    cached,
                    spec=spec,
                    template=template,
                    request_payload=request_payload,
                    status_label="success",
                )

        attempts: list[str] = []
        last_error: Exception | None = None
        route = self._route_configs.get(spec.prompt_name) or self._fallback_route(spec)

        for level, (provider_name, model) in (
            ("primary", (route.primary_provider, route.primary_model)),
            ("fallback", (route.fallback_provider or "offline", route.fallback_model or "offline-v1")),
            ("offline", ("offline", "offline-v1")),
        ):
            if not provider_name:
                continue
            provider = self.registry.get(provider_name)
            if provider is None:
                attempts.append(f"{level}:missing:{provider_name}")
                continue
            if not provider.is_available():
                attempts.append(f"{level}:disabled:{provider_name}")
                continue
            if self._circuit_is_open(provider_name):
                attempts.append(f"{level}:circuit_open:{provider_name}")
                continue

            request = GenerationRequest(
                prompt_name=template.name,
                prompt_version=template.version,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=template.temperature,
                top_p=template.top_p,
                max_output_tokens=template.max_output_tokens,
            )

            try:
                response_obj: Any = await _call_provider(provider, request)
            except CircuitOpen as exc:
                attempts.append(f"{level}:circuit_open:{provider_name}")
                last_error = exc
                continue
            except ProviderError as exc:
                attempts.append(f"{level}:error:{provider_name}:{exc}")
                last_error = exc
                self._register_failure(provider_name)
                continue
            except AIServiceUnavailable as exc:
                attempts.append(f"{level}:unavailable:{provider_name}:{exc}")
                last_error = exc
                self._register_failure(provider_name)
                continue

            self._register_success(provider_name)
            response: GenerationResponse = cast(GenerationResponse, response_obj)
            provider_status = _to_status(level)
            status_label = _status_label(level)

            prompt_version = PromptVersion(
                name=template.name,
                version=template.version,
                provider=provider.name,
                model=response.model,
                input_hash=hash_payload(request_payload),
                output_hash=hash_payload(response.text),
                token_usage=response.token_usage,
                latency_ms=response.latency_ms,
                status=status_label,
            )

            if opts.use_cache and response.provider_status != ProviderStatus.OFFLINE:
                await self._cache_store(template, request_payload, response)

            return ProviderOutput(
                text=response.text,
                structured=response.structured,
                prompt_version=prompt_version,
                provider_status=provider_status,
            )

        # 全部失败 → 返回离线兜底（不抛错，除非 opts.raise_on_total_failure）
        offline = self.registry.get("offline") or self.registry.get(route.fallback_provider or "")
        if offline is None:
            attempts.append("offline:missing")
            if opts.raise_on_total_failure:
                raise AllProvidersFailed("all providers missing", attempts=attempts) from last_error
            return self._empty_output(spec, template, request_payload, attempts)

        offline_response = await _call_provider(offline, _offline_request(template, system_prompt, user_prompt))
        prompt_version = PromptVersion(
            name=template.name,
            version=template.version,
            provider=offline.name,
            model=offline_response.model,
            input_hash=hash_payload(request_payload),
            output_hash=hash_payload(offline_response.text),
            token_usage=offline_response.token_usage,
            latency_ms=offline_response.latency_ms,
            status="offline_used",
        )
        if last_error is not None:
            logger.warning(
                "ai.router.all_providers_failed job_id=%s attempts=%s last_error=%s",
                spec.job_id,
                attempts,
                last_error,
            )
        return ProviderOutput(
            text=offline_response.text,
            structured=offline_response.structured,
            prompt_version=prompt_version,
            provider_status=ProviderStatus.OFFLINE,
        )

    def _resolve_prompt(self, spec: JobSpec) -> PromptTemplate:
        try:
            return self.prompts.get(spec.prompt_name, spec.prompt_version)
        except KeyError:
            return load_prompt(spec.prompt_name, spec.prompt_version, registry=self.prompts)

    def _fallback_route(self, spec: JobSpec) -> RouteConfig:
        return RouteConfig(
            scene=spec.scene,
            prompt_name=spec.prompt_name,
            primary_provider="fake",
            primary_model="qwen-plus",
            fallback_provider="offline",
            fallback_model="offline-v1",
        )

    def _wrap_response(
        self,
        cached_payload: Mapping[str, Any],
        *,
        spec: JobSpec,
        template: PromptTemplate,
        request_payload: Mapping[str, Any],
        status_label: str,
    ) -> ProviderOutput:
        response = response_from_cache_payload(cached_payload)
        prompt_version = PromptVersion(
            name=template.name,
            version=template.version,
            provider=response.provider or "cache",
            model=response.model,
            input_hash=hash_payload(request_payload),
            output_hash=hash_payload(response.text),
            token_usage=response.token_usage,
            latency_ms=response.latency_ms,
            status="cached",
        )
        provider_status = (
            ProviderStatus(response.provider_status)
            if isinstance(response.provider_status, str)
            else response.provider_status
        )
        return ProviderOutput(
            text=response.text,
            structured=response.structured,
            prompt_version=prompt_version,
            provider_status=provider_status,
        )

    def _empty_output(
        self,
        spec: JobSpec,
        template: PromptTemplate,
        request_payload: Mapping[str, Any],
        attempts: list[str],
    ) -> ProviderOutput:
        empty = {
            "summary": "无可用 Provider，已返回空结果",
            "offlineUsed": True,
            "attempts": attempts,
        }
        text = str(empty)
        prompt_version = PromptVersion(
            name=template.name,
            version=template.version,
            provider="none",
            model="",
            input_hash=hash_payload(request_payload),
            output_hash=hash_payload(text),
            token_usage=TokenUsage(),
            latency_ms=0,
            status="failed",
        )
        return ProviderOutput(
            text=text,
            structured=empty,
            prompt_version=prompt_version,
            provider_status=ProviderStatus.OFFLINE,
        )

    async def _cache_lookup(self, template: PromptTemplate, payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
        key = cache_key(template.name, template.model, template.version, payload)
        result: Any = await self._cache.get(key)
        return cast(Mapping[str, Any] | None, result)

    async def _cache_store(
        self,
        template: PromptTemplate,
        payload: Mapping[str, Any],
        response: GenerationResponse,
    ) -> None:
        key = cache_key(template.name, template.model, template.version, payload)
        await self._cache.set(key, response_to_cache_payload(response), ttl_seconds=self.settings.cache_ttl_seconds)

    def _circuit_is_open(self, provider_name: str) -> bool:
        state = self._circuits.get(provider_name)
        if state is None:
            return False
        return state.is_open(
            self.settings.circuit_breaker_failures,
            self.settings.circuit_breaker_cooldown_seconds,
        )

    def _register_failure(self, provider_name: str) -> None:
        state = self._circuits.setdefault(provider_name, _CircuitState())
        state.failures += 1
        if state.failures >= self.settings.circuit_breaker_failures and state.opened_at == 0.0:
            state.opened_at = time.monotonic()
            logger.warning(
                "ai.router.circuit_open provider=%s failures=%d cooldown=%.0fs",
                provider_name,
                state.failures,
                self.settings.circuit_breaker_cooldown_seconds,
            )

    def _register_success(self, provider_name: str) -> None:
        self._circuits.pop(provider_name, None)


async def _call_provider(provider: Provider, request: GenerationRequest) -> GenerationResponse:
    generate = provider.generate
    if not inspect.iscoroutinefunction(generate):
        return cast(GenerationResponse, generate(request))
    return cast(GenerationResponse, await generate(request))


def _to_status(level: str) -> ProviderStatus:
    return {
        "primary": ProviderStatus.PRIMARY,
        "fallback": ProviderStatus.FALLBACK,
        "offline": ProviderStatus.OFFLINE,
    }[level]


def _status_label(level: str) -> str:
    return {
        "primary": "success",
        "fallback": "fallback_used",
        "offline": "offline_used",
    }[level]


def _offline_request(template: PromptTemplate, system_prompt: str, user_prompt: str) -> GenerationRequest:
    return GenerationRequest(
        prompt_name=template.name,
        prompt_version=template.version,
        model="offline-v1",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=template.temperature,
        top_p=template.top_p,
        max_output_tokens=template.max_output_tokens,
    )


_ROUTER: ModelRouter | None = None
_ROUTER_LOCK = asyncio.Lock()


async def get_router() -> ModelRouter:
    global _ROUTER
    async with _ROUTER_LOCK:
        if _ROUTER is None:
            router = ModelRouter(
                registry=build_default_registry(get_settings()),
                prompts=load_prompt.__globals__["build_default_registry"](),
            )
            router.register_default_routes()
            _ROUTER = router
        return _ROUTER


def reset_router_for_tests() -> None:
    """仅测试使用：清除单例。"""

    global _ROUTER
    _ROUTER = None


async def invoke(spec: JobSpec, *, payload: Mapping[str, Any] | None = None) -> ProviderOutput:
    """便捷函数：从默认 Router 调用一次。"""

    router = await get_router()
    return await router.invoke(spec, payload=payload)


__all__ = [
    "ModelRouter",
    "RouteConfig",
    "RouterOptions",
    "get_router",
    "invoke",
    "reset_router_for_tests",
]
