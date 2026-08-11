"""Worker 基类测试。"""

from __future__ import annotations

import pytest

from app.ai.schemas import JobStatus, ProviderStatus
from app.workers.base import AbortError, M7Task, run_task_handler


class _Task(M7Task):
    """用于测试的最小 Task。"""

    name = "app.workers.tests.dummy"
    scene = "dummy"
    prompt_name = "tender_parse"
    prompt_version = "1.0.0"


def test_m7_task_builds_spec() -> None:
    task = _Task()
    spec = task._build_spec("job-1", {"aggregateId": "a-1", "aggregateType": "bidTask", "tenantId": "t-1"})
    assert spec.job_id == "job-1"
    assert spec.aggregate_id == "a-1"
    assert spec.aggregate_type == "bidTask"
    assert spec.tenant_id == "t-1"


def test_m7_task_idempotency_key_stable() -> None:
    task = _Task()
    key1 = task._idempotency_key("job-1", None)
    key2 = task._idempotency_key("job-1", None)
    assert key1 == key2


def test_m7_task_idempotency_key_uses_user_value() -> None:
    task = _Task()
    assert task._idempotency_key("job-1", "abc") == "idemp:app.workers.tests.dummy:abc"


def test_m7_task_makes_success_result() -> None:
    from app.ai.schemas import PromptVersion, TokenUsage

    task = _Task()
    result = task.make_success_result(
        job_id="job-1",
        provider_used=ProviderStatus.PRIMARY,
        output={"k": "v"},
        prompt_versions=[
            PromptVersion(
                name="tender_parse",
                version="1.0.0",
                provider="fake",
                model="qwen-plus",
                input_hash="x",
                output_hash="y",
                token_usage=TokenUsage(),
                latency_ms=10,
                status="success",
            )
        ],
        token_usage=TokenUsage(prompt=1, completion=2, total=3),
    )
    assert result.status == JobStatus.SUCCEEDED
    assert result.provider_used == ProviderStatus.PRIMARY
    assert result.output == {"k": "v"}


def test_m7_task_makes_partial_result() -> None:
    from app.ai.schemas import PromptVersion, TokenUsage

    task = _Task()
    result = task.make_partial_result(
        job_id="job-1",
        output={"x": "y"},
        prompt_versions=[
            PromptVersion(
                name="tender_parse",
                version="1.0.0",
                provider="offline",
                model="offline-v1",
                input_hash="x",
                output_hash="y",
                token_usage=TokenUsage(),
                latency_ms=0,
                status="offline_used",
            )
        ],
        token_usage=TokenUsage(),
        error_code="AI_PROVIDER_UNAVAILABLE",
        error_message="down",
    )
    assert result.status == JobStatus.SUCCEEDED
    assert result.provider_used == ProviderStatus.OFFLINE
    assert result.output["offlineUsed"] is True
    assert result.error_code == "AI_PROVIDER_UNAVAILABLE"


def test_m7_task_makes_failure_result() -> None:
    task = _Task()
    result = task.make_failure_result(
        job_id="job-1",
        prompt_versions=[],
        error_code="INTERNAL_ERROR",
        error_message="boom",
    )
    assert result.status == JobStatus.FAILED
    assert result.provider_used == ProviderStatus.OFFLINE
    assert result.error_code == "INTERNAL_ERROR"


def test_run_task_handler_returns_dict() -> None:
    from app.ai.schemas import JobResult, JobStatus, ProviderStatus, TokenUsage

    task = _Task()
    handler = run_task_handler(
        task,
        lambda spec, payload: JobResult(
            job_id=spec.job_id,
            status=JobStatus.SUCCEEDED,
            provider_used=ProviderStatus.PRIMARY,
            output={"ok": True},
            prompt_versions=[],
            token_usage=TokenUsage(),
        ),
    )
    result = handler("job-1", {"aggregateId": "a-1"})
    assert result["status"] == "succeeded"
    assert result["output"] == {"ok": True}


def test_run_task_handler_returns_mapping_dict_directly() -> None:
    task = _Task()
    handler = run_task_handler(task, lambda spec, payload: {"already": "dict"})
    result = handler("job-1", {})
    assert result == {"already": "dict"}


def test_run_task_handler_catches_exception() -> None:
    task = _Task()

    def failing(spec, payload):
        raise RuntimeError("unexpected")

    handler = run_task_handler(task, failing)
    result = handler("job-1", {})
    assert result["status"] == "failed"
    assert result["errorCode"] == "INTERNAL_ERROR"
    assert "unexpected" in result["errorMessage"]


def test_run_task_handler_catches_all_providers_failed() -> None:
    from app.ai.errors import AllProvidersFailed

    task = _Task()

    def failing(spec, payload):
        raise AllProvidersFailed("all failed", attempts=["fake:error", "offline:error"])

    handler = run_task_handler(task, failing)
    result = handler("job-1", {})
    assert result["status"] == "failed"
    assert result["errorCode"] == "AI_PROVIDER_UNAVAILABLE"


def test_run_task_handler_catches_circuit_open() -> None:
    from app.ai.errors import CircuitOpen

    task = _Task()

    def failing(spec, payload):
        raise CircuitOpen("circuit", provider="fake")

    handler = run_task_handler(task, failing)
    result = handler("job-1", {})
    assert result["status"] == "failed"
    assert result["errorCode"] == "AI_PROVIDER_UNAVAILABLE"


def test_run_task_handler_reraises_retryable_provider_error() -> None:
    from app.ai.errors import ProviderTimeout

    task = _Task()

    def failing(spec, payload):
        raise ProviderTimeout("temporary timeout", provider="fake")

    handler = run_task_handler(task, failing)
    with pytest.raises(ProviderTimeout):
        handler("job-1", {})


def test_run_task_handler_rejects_invalid_return() -> None:
    task = _Task()

    def returning_int(spec, payload):
        return 123

    handler = run_task_handler(task, returning_int)
    with pytest.raises(TypeError):
        handler("job-1", {})


def test_abort_error_is_exception() -> None:
    assert issubclass(AbortError, Exception)
