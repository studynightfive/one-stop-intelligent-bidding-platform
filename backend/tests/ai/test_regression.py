"""离线回归测试：固定样本 → 稳定结构。"""

from __future__ import annotations

import pytest

from app.ai.prompts.registry import build_default_registry as build_prompts
from app.ai.providers.factory import build_default_registry
from app.ai.router import ModelRouter, reset_router_for_tests
from app.ai.schemas import JobSpec
from app.ai.settings import AISettings
from tests.ai.fixtures import SAMPLES


def _router() -> ModelRouter:
    reset_router_for_tests()
    settings = AISettings.from_env()
    return ModelRouter(
        registry=build_default_registry(settings),
        prompts=build_prompts(),
    )


@pytest.mark.parametrize("sample", list(SAMPLES), ids=[s.prompt_name for s in SAMPLES])
@pytest.mark.asyncio
async def test_sample_returns_required_keys(sample) -> None:
    router = _router()
    spec = JobSpec(
        job_id=f"job-{sample.prompt_name}",
        scene=sample.prompt_name,
        aggregate_id="agg",
        aggregate_type="bidTask",
        prompt_name=sample.prompt_name,
        prompt_version=sample.prompt_version,
        input_payload=sample.payload,
    )
    output = await router.invoke(spec, payload=sample.payload)
    assert output.text, f"{sample.prompt_name} 应返回非空文本"
    structured = output.structured or {}
    for key in sample.required_keys:
        assert key in structured, f"{sample.prompt_name} 应包含字段 {key}"
    assert output.prompt_version.name == sample.prompt_name
    assert output.prompt_version.version == sample.prompt_version


@pytest.mark.asyncio
async def test_regression_tender_parse_summary_present() -> None:
    router = _router()
    spec = JobSpec(
        job_id="job-regression-tender",
        scene="tender_parse",
        aggregate_id="agg",
        aggregate_type="bidTask",
        prompt_name="tender_parse",
        prompt_version="1.0.0",
        input_payload={},
    )
    output = await router.invoke(
        spec,
        payload={
            "projectName": "智慧校园",
            "rawText": "## 背景\n推进数字化\n\n## 范围\n教学管理平台\n",
        },
    )
    structured = output.structured or {}
    assert "summary" in structured
    assert structured.get("sectionCount", 0) >= 1


@pytest.mark.asyncio
async def test_regression_evaluation_score_returns_overall() -> None:
    router = _router()
    spec = JobSpec(
        job_id="job-regression-score",
        scene="evaluation_score",
        aggregate_id="agg",
        aggregate_type="evaluation",
        prompt_name="evaluation_score",
        prompt_version="1.0.0",
        input_payload={},
    )
    output = await router.invoke(
        spec,
        payload={"scoringCriteria": [{"name": "技术方案", "maxScore": "100"}], "supplierResponse": {}},
    )
    structured = output.structured or {}
    assert "scores" in structured
    assert "overall" in structured
