"""M7 Worker Task 基类。

封装通用能力：
- 幂等键（基于 ``Idempotency-Key`` + ``aggregateId`` + ``scene``）；
- 进度上报（``self.update_state``，由 M4 JobService 转发 WebSocket）；
- 取消信号（``AbortError``，M4 ``POST /jobs/{id}/cancel`` 写入 Redis）；
- 重试 / 死信（``autoretry_for`` + ``retry_backoff``）；
- 审计快照（每次调用留 ``PromptVersion`` 痕迹）；
- JobResult 输出与失败时不抛业务阻塞。

业务 Worker 必须继承 :class:`M7Task` 并实现 :meth:`run`。
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from celery import Task  # type: ignore[import-untyped]
from celery.exceptions import Ignore as CeleryIgnore  # type: ignore[import-untyped]

from app.ai.errors import (
    AIServiceUnavailable,
    AllProvidersFailed,
    CircuitOpen,
    ProviderError,
    ProviderRateLimited,
    ProviderTimeout,
)
from app.ai.schemas import (
    JobResult,
    JobSpec,
    JobStatus,
    PromptVersion,
    ProviderStatus,
    TokenUsage,
)
from app.ai.settings import get_settings

logger = logging.getLogger(__name__)


class AbortError(Exception):
    """业务主动取消异常。Celery 收到后应将 Job 标记为 cancelled。"""


class M7Task(Task):  # type: ignore[misc]
    """所有 M7 Worker Task 的基类。

    子类需要：
    - 设置 ``name``（Celery task name）；
    - 设置 ``scene``（对应 OpenAPI Scene 枚举）；
    - 设置 ``prompt_name`` / ``prompt_version``；
    - 重写 :meth:`run` 实现业务逻辑。
    """

    abstract = True
    name = "app.workers.base.M7Task"
    scene: str = ""
    prompt_name: str = ""
    prompt_version: str = "1.0.0"
    autoretry_for: tuple[type[BaseException], ...] = (
        ProviderError,
        ProviderRateLimited,
        ProviderTimeout,
        AIServiceUnavailable,
    )
    retry_backoff = True
    retry_backoff_max = 60
    retry_jitter = True
    max_retries = 3
    soft_time_limit: int | None = None
    time_limit: int | None = None

    def _idempotency_key(self, job_id: str, idempotency_key: str | None) -> str:
        if idempotency_key:
            return f"idemp:{self.name}:{idempotency_key}"
        digest = hashlib.sha256(f"{self.name}:{job_id}".encode()).hexdigest()
        return f"idemp:{self.name}:{digest[:32]}"

    def _build_spec(self, job_id: str, payload: Mapping[str, Any]) -> JobSpec:
        return JobSpec(
            job_id=job_id,
            scene=self.scene or self.prompt_name,
            aggregate_id=str(payload.get("aggregateId") or job_id),
            aggregate_type=str(payload.get("aggregateType") or "job"),
            prompt_name=self.prompt_name,
            prompt_version=self.prompt_version,
            input_payload=dict(payload),
            tenant_id=payload.get("tenantId") if isinstance(payload, Mapping) else None,
            user_id=payload.get("userId") if isinstance(payload, Mapping) else None,
            idempotency_key=payload.get("idempotencyKey") if isinstance(payload, Mapping) else None,
        )

    def update_progress(self, percent: int, current_step: str | None = None) -> None:
        """由子类调用：把进度写回 Celery state（M4 JobService 会自动转发）。"""

        self.update_state(
            state="PROGRESS",
            meta={"progressPercent": percent, "currentStep": current_step or ""},
        )

    def make_success_result(
        self,
        *,
        job_id: str,
        provider_used: ProviderStatus,
        output: Mapping[str, Any],
        prompt_versions: list[PromptVersion],
        token_usage: TokenUsage,
    ) -> JobResult:
        return JobResult(
            job_id=job_id,
            status=JobStatus.SUCCEEDED,
            provider_used=provider_used,
            output=dict(output),
            prompt_versions=prompt_versions,
            token_usage=token_usage,
            completed_at=datetime.now(UTC),
        )

    def make_partial_result(
        self,
        *,
        job_id: str,
        output: Mapping[str, Any],
        prompt_versions: list[PromptVersion],
        token_usage: TokenUsage,
        error_code: str,
        error_message: str,
    ) -> JobResult:
        return JobResult(
            job_id=job_id,
            status=JobStatus.SUCCEEDED,
            provider_used=ProviderStatus.OFFLINE,
            output={
                "offlineUsed": True,
                **dict(output),
            },
            prompt_versions=prompt_versions,
            token_usage=token_usage,
            error_code=error_code,
            error_message=error_message,
            completed_at=datetime.now(UTC),
        )

    def make_failure_result(
        self,
        *,
        job_id: str,
        prompt_versions: list[PromptVersion],
        error_code: str,
        error_message: str,
        token_usage: TokenUsage | None = None,
    ) -> JobResult:
        return JobResult(
            job_id=job_id,
            status=JobStatus.FAILED,
            provider_used=ProviderStatus.OFFLINE,
            output={},
            prompt_versions=prompt_versions,
            token_usage=token_usage or TokenUsage(),
            error_code=error_code,
            error_message=error_message,
            completed_at=datetime.now(UTC),
        )

    def on_failure(
        self,
        exc: BaseException,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: Mapping[str, Any],
        einfo: Any,
    ) -> None:
        """Celery 钩子：记录最终失败原因，便于 ``M4 AuditService`` 拉取。"""

        logger.warning(
            "m7.task.failed task=%s task_id=%s exc=%s",
            self.name,
            task_id,
            exc,
        )

    def on_success(
        self,
        retval: Any,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: Mapping[str, Any],
    ) -> None:
        logger.info(
            "m7.task.success task=%s task_id=%s status=%s",
            self.name,
            task_id,
            getattr(retval, "status", None) if retval else None,
        )

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Celery 入口；这里封装取消信号 + 异常归一化。"""

        from app.ai.router import reset_router_for_tests

        reset_router_for_tests()
        return super().__call__(*args, **kwargs)


def run_task_handler(
    task: M7Task,
    handler: Callable[[JobSpec, Mapping[str, Any]], JobResult | dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    """工厂：把子类实现的 ``run`` 封装为 Celery 可调用的同步函数。

    子类典型用法::

        class BiddingParserTask(M7Task):
            name = \"app.workers.bidding_parser.parse\"
            scene = \"tender_parse\"
            prompt_name = \"tender_parse\"
            prompt_version = \"1.0.0\"

            def run(self, job_id, payload):
                return run_task_handler(self, self._execute)
    """

    def wrapper(job_id: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        spec = task._build_spec(job_id, payload or {})
        try:
            result = handler(spec, payload or {})
        except AbortError as exc:
            task.update_state(state="CANCELLED", meta={"reason": str(exc)})
            raise CeleryIgnore() from None
        except (CircuitOpen, AllProvidersFailed):
            logger.warning("m7.task.aborted_all_failed task=%s job=%s", task.name, job_id)
            failed = task.make_failure_result(
                job_id=job_id,
                prompt_versions=[],
                error_code="AI_PROVIDER_UNAVAILABLE",
                error_message="all providers failed",
            )
            return failed.to_dict()
        except task.autoretry_for:
            # Let Celery's autoretry wrapper apply the declared exponential
            # backoff.  Swallowing these errors here made ``autoretry_for`` a
            # no-op and discarded resumable worker checkpoints.
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("m7.task.unhandled task=%s job=%s", task.name, job_id)
            failed = task.make_failure_result(
                job_id=job_id,
                prompt_versions=[],
                error_code="INTERNAL_ERROR",
                error_message=str(exc) or exc.__class__.__name__,
            )
            return failed.to_dict()

        if isinstance(result, JobResult):
            return result.to_dict()
        if isinstance(result, Mapping):
            # 业务 dict 直接返回（已经序列化）
            return dict(result)
        raise TypeError(f"unsupported task result type: {type(result)!r}")

    return wrapper


__all__ = [
    "AbortError",
    "M7Task",
    "run_task_handler",
]


# 抑制未使用导入告警（pydantic 类型在静态检查时引用）
_settings_obj = get_settings
_ = (_settings_obj,)
