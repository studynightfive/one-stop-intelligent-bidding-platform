"""离线 AI 路由集成测试。"""

from __future__ import annotations

import pytest

from app.ai.prompts.registry import build_default_registry as build_prompts
from app.ai.providers.factory import build_default_registry
from app.ai.router import ModelRouter, RouterOptions, reset_router_for_tests
from app.ai.schemas import JobSpec, ProviderStatus
from app.ai.settings import AISettings


def _build_router() -> ModelRouter:
    reset_router_for_tests()
    settings = AISettings.from_env()
    router = ModelRouter(
        registry=build_default_registry(settings),
        prompts=build_prompts(),
    )
    router.register_default_routes()
    return router


@pytest.mark.asyncio
async def test_router_invokes_fake_provider() -> None:
    router = _build_router()
    spec = JobSpec(
        job_id="job-1",
        scene="tender_parse",
        aggregate_id="agg-1",
        aggregate_type="bidTask",
        prompt_name="tender_parse",
        prompt_version="1.0.0",
        input_payload={"projectName": "Demo"},
    )
    output = await router.invoke(spec, payload={"projectName": "Demo", "rawText": "Hi"})
    assert output.provider_status in {ProviderStatus.PRIMARY, ProviderStatus.OFFLINE}
    assert output.text  # 不为空
    assert output.prompt_version.name == "tender_parse"
    assert output.prompt_version.version == "1.0.0"


@pytest.mark.asyncio
async def test_router_invokes_all_scenes() -> None:
    """每个场景都能路由成功（结构稳定）。"""

    router = _build_router()
    scenes = [
        ("tender_parse", "tender_parse"),
        ("requirement_extract", "requirement_extract"),
        ("material_match", "material_match"),
        ("bid_review", "bid_review"),
        ("bid_generate", "bid_generate"),
        ("risk_check", "risk_check"),
        ("evaluation_check", "evaluation_check"),
        ("evaluation_score", "evaluation_score"),
        ("report_generate", "report_generate"),
    ]
    for scene, prompt_name in scenes:
        spec = JobSpec(
            job_id=f"job-{scene}",
            scene=scene,
            aggregate_id="agg",
            aggregate_type="bidTask",
            prompt_name=prompt_name,
            prompt_version="1.0.0",
            input_payload={},
        )
        output = await router.invoke(spec, payload={})
        assert output.text, f"{scene} should produce output"
        assert output.prompt_version.name == scene


@pytest.mark.asyncio
async def test_router_cache_avoids_repeat_call() -> None:
    router = _build_router()
    spec = JobSpec(
        job_id="job-cache",
        scene="tender_parse",
        aggregate_id="agg",
        aggregate_type="bidTask",
        prompt_name="tender_parse",
        prompt_version="1.0.0",
        input_payload={"projectName": "Demo"},
    )
    payload = {"projectName": "Demo", "rawText": "cached"}
    first = await router.invoke(spec, payload=payload)
    second = await router.invoke(spec, payload=payload)
    assert first.text == second.text


@pytest.mark.asyncio
async def test_router_falls_back_when_primary_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """主 Provider 不可用时回落到离线 Provider。"""

    monkeypatch.setenv("AI_FAKE_PROVIDER", "false")
    router = _build_router()
    spec = JobSpec(
        job_id="job-fb",
        scene="tender_parse",
        aggregate_id="agg",
        aggregate_type="bidTask",
        prompt_name="tender_parse",
        prompt_version="1.0.0",
        input_payload={},
    )
    output = await router.invoke(spec, payload={})
    # 主 Provider "fake" 不在注册表 → 路由到 fallback/offline
    assert output.provider_status in {ProviderStatus.FALLBACK, ProviderStatus.OFFLINE}
    assert output.text


@pytest.mark.asyncio
async def test_router_circuit_breaker_opens() -> None:
    """连续失败打开熔断器，路由跳过该 Provider。"""

    from app.ai.errors import ProviderError
    from app.ai.providers.base import GenerationRequest, GenerationResponse
    from app.ai.router import RouteConfig

    class FailingProvider:
        name = "failing"

        def __init__(self) -> None:
            self.calls = 0

        def is_available(self) -> bool:
            return True

        async def generate(self, request: GenerationRequest) -> GenerationResponse:  # noqa: D401
            self.calls += 1
            raise ProviderError("boom", provider=self.name)

    router = _build_router()
    failing = FailingProvider()
    router.registry.register(failing)

    # 主 = failing，备 = offline（fallback 命中）
    router.register_route(
        RouteConfig(
            scene="tender_parse",
            prompt_name="tender_parse",
            primary_provider="failing",
            primary_model="x",
            fallback_provider="offline",
            fallback_model="offline-v1",
        )
    )

    # 连续 3 次失败后熔断器打开
    for _ in range(3):
        spec = JobSpec(
            job_id="job-cb",
            scene="tender_parse",
            aggregate_id="agg",
            aggregate_type="bidTask",
            prompt_name="tender_parse",
            prompt_version="1.0.0",
            input_payload={},
        )
        await router.invoke(spec, payload={"x": "y"}, options=RouterOptions(use_cache=False))

    # 熔断打开后，failing 不应被再次调用；路由命中 fallback
    previous_calls = failing.calls
    spec = JobSpec(
        job_id="job-cb-2",
        scene="tender_parse",
        aggregate_id="agg",
        aggregate_type="bidTask",
        prompt_name="tender_parse",
        prompt_version="1.0.0",
        input_payload={},
    )
    output = await router.invoke(spec, payload={"x": "y2"}, options=RouterOptions(use_cache=False))
    assert failing.calls == previous_calls
    assert output.provider_status in {ProviderStatus.FALLBACK, ProviderStatus.OFFLINE}
