"""Create platform jobs and dispatch their M7 worker tasks."""

from __future__ import annotations

import asyncio
import importlib
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.database import get_db_context
from app.domains.jobs.models.job import Job, JobStatus, JobType
from app.domains.jobs.services.job_service import JobService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WorkerRoute:
    module: str
    task_name: str


_WORKER_ROUTES: dict[str, WorkerRoute] = {
    "bid.parse_tender": WorkerRoute("app.workers.bidding_parser", "app.workers.bidding_parser.parse"),
    "bid.material_match": WorkerRoute("app.workers.bidding_matcher", "app.workers.bidding_matcher.match"),
    "bid.template_generate": WorkerRoute("app.workers.bidding_generator", "app.workers.bidding_generator.generate"),
    "bid.review": WorkerRoute("app.workers.bidding_auditor", "app.workers.bidding_auditor.review"),
    "bid.document_generate": WorkerRoute("app.workers.bidding_generator", "app.workers.bidding_generator.generate"),
    "evaluation.material_check": WorkerRoute("app.workers.eval_integrity", "app.workers.eval_integrity.check"),
    "evaluation_check": WorkerRoute("app.workers.eval_integrity", "app.workers.eval_integrity.check"),
    "evaluation.risk_check": WorkerRoute("app.workers.eval_risk", "app.workers.eval_risk.check"),
    "risk_check": WorkerRoute("app.workers.eval_risk", "app.workers.eval_risk.check"),
    "evaluation.ai_scoring": WorkerRoute("app.workers.eval_scorer", "app.workers.eval_scorer.score"),
    "evaluation_score": WorkerRoute("app.workers.eval_scorer", "app.workers.eval_scorer.score"),
    "evaluation.report_generate": WorkerRoute("app.workers.eval_reporter", "app.workers.eval_reporter.generate"),
    "report_generate": WorkerRoute("app.workers.eval_reporter", "app.workers.eval_reporter.generate"),
}


class JobDispatcher:
    """Persist jobs, invoke mapped Celery workers and synchronize outcomes."""

    def __init__(self, celery: Any | None = None) -> None:
        self._celery = celery

    async def dispatch(
        self,
        user_id: UUID,
        tenant_id: UUID,
        job_type: JobType,
        input_data: dict[str, Any] | None = None,
        project_id: UUID | None = None,
    ) -> Job:
        payload = dict(input_data or {})
        async with get_db_context() as db:
            service = JobService(db)
            job = await service.create_job(
                user_id=user_id,
                tenant_id=tenant_id,
                job_type=job_type,
                input_data=payload,
                project_id=project_id,
            )
            route = resolve_worker_route(payload)
            if route is None:
                return job

            celery_app = self._celery_app()
            importlib.import_module(route.module)
            task = celery_app.tasks.get(route.task_name)
            if task is None:
                error = _job_error("WORKER_NOT_REGISTERED", f"worker task is not registered: {route.task_name}")
                await service.mark_job_failed(job.id, error=error)
                raise RuntimeError(error["message"])
            # Older M7 modules register task instances directly on the registry.
            # Bind the resolved instance to this concrete app before ``apply`` or
            # ``apply_async`` so Celery does not fall back to the process default app.
            task = celery_app.register_task(task)

            try:
                if bool(celery_app.conf.task_always_eager):
                    job = await service.mark_job_started(job.id)
                    eager_result = await asyncio.to_thread(
                        task.apply,
                        args=[str(job.id), payload],
                        task_id=str(job.id),
                    )
                    await service.bind_celery_task_id(job.id, str(eager_result.id or job.id))
                    worker_result = await asyncio.to_thread(lambda: eager_result.get(propagate=False))
                    if isinstance(worker_result, BaseException):
                        return await service.mark_job_failed(
                            job.id,
                            error=_job_error("WORKER_EXECUTION_FAILED", str(worker_result) or "worker failed"),
                        )
                    return await _persist_worker_result(service, job.id, worker_result)

                async_result = await asyncio.to_thread(
                    task.apply_async,
                    args=[str(job.id), payload],
                    task_id=str(job.id),
                )
                await service.bind_celery_task_id(job.id, str(async_result.id))
                return job
            except Exception as exc:
                await service.mark_job_failed(
                    job.id,
                    error=_job_error("WORKER_DISPATCH_FAILED", str(exc) or exc.__class__.__name__),
                )
                raise

    async def dispatch_and_start(
        self,
        user_id: UUID,
        tenant_id: UUID,
        job_type: JobType,
        input_data: dict[str, Any] | None = None,
        project_id: UUID | None = None,
    ) -> Job:
        """Create a job and mark it running without dispatching a Celery task."""

        async with get_db_context() as db:
            service = JobService(db)
            job = await service.create_job(
                user_id=user_id,
                tenant_id=tenant_id,
                job_type=job_type,
                input_data=input_data,
                project_id=project_id,
            )
            return await service.mark_job_started(job.id)

    async def refresh(
        self,
        job_or_id: Job | UUID,
        *,
        service: JobService | None = None,
    ) -> Job | None:
        """Synchronize a queued/running DB record from the Celery result backend."""

        if service is not None:
            job = job_or_id if isinstance(job_or_id, Job) else await service.get_job_by_id(job_or_id)
            return await self._refresh_with_service(service, job)
        async with get_db_context() as db:
            scoped_service = JobService(db)
            job_id = job_or_id.id if isinstance(job_or_id, Job) else job_or_id
            job = await scoped_service.get_job_by_id(job_id)
            return await self._refresh_with_service(scoped_service, job)

    async def _refresh_with_service(self, service: JobService, job: Job | None) -> Job | None:
        if job is None or job.is_finished or not job.celery_task_id:
            return job
        job_id = job.id
        try:
            async_result = self._celery_app().AsyncResult(job.celery_task_id)
            state = str(async_result.state).upper()
            if state == "SUCCESS":
                return await _persist_worker_result(service, job.id, async_result.result)
            if state == "FAILURE":
                return await service.mark_job_failed(
                    job.id,
                    error=_job_error(
                        "WORKER_EXECUTION_FAILED",
                        str(async_result.result) or "worker failed",
                    ),
                )
            if state == "PROGRESS":
                metadata = async_result.info if isinstance(async_result.info, Mapping) else {}
                return await service.update_job_status(
                    job.id,
                    JobStatus.RUNNING,
                    progress_percent=int(metadata.get("progressPercent", job.progress_percent) or 0),
                    current_step=str(metadata.get("currentStep") or job.current_step or "任务执行中"),
                )
            if state in {"STARTED", "RETRY"} and job.status == JobStatus.QUEUED:
                return await service.mark_job_started(job.id)
            if state == "REVOKED" and job.is_cancellable:
                return await service.cancel_job(job.id)
        except Exception:
            logger.warning("unable to refresh Celery job %s", job_id, exc_info=True)
        return job

    async def revoke(self, celery_task_id: str | None) -> None:
        """Revoke a queued/running worker without terminating its process."""

        if not celery_task_id:
            return
        try:
            await asyncio.to_thread(self._celery_app().control.revoke, celery_task_id, terminate=False)
        except Exception:
            logger.warning("unable to revoke Celery task %s", celery_task_id, exc_info=True)

    def _celery_app(self) -> Any:
        if self._celery is None:
            from app.workers.celery_app import celery_app

            self._celery = celery_app
        return self._celery


def resolve_worker_route(input_data: Mapping[str, Any] | None) -> WorkerRoute | None:
    if not input_data:
        return None
    scene = str(input_data.get("m5JobType") or input_data.get("m6JobType") or "")
    return _WORKER_ROUTES.get(scene)


async def _persist_worker_result(service: JobService, job_id: UUID, raw: Any) -> Job:
    if not isinstance(raw, Mapping):
        return await service.mark_job_failed(
            job_id,
            error=_job_error("INVALID_WORKER_RESULT", "worker result must be an object"),
        )
    result = dict(raw)
    worker_status = str(result.get("status") or "failed").lower()
    if worker_status == "succeeded":
        return await service.mark_job_succeeded(job_id, result=result)
    if worker_status == "cancelled":
        job = await service.get_job_by_id(job_id)
        if job is not None and job.is_cancellable:
            return await service.cancel_job(job_id)
    error = _job_error(
        str(result.get("errorCode") or "WORKER_EXECUTION_FAILED"),
        str(result.get("errorMessage") or "worker returned a failed result"),
        retryable=bool(result.get("retryable", False)),
    )
    return await service.update_job_status(
        job_id,
        JobStatus.FAILED,
        current_step="任务执行失败",
        result=result,
        error=error,
    )


def _job_error(code: str, message: str, *, retryable: bool = False) -> dict[str, Any]:
    return {"code": code, "message": message, "retryable": retryable}


job_dispatcher = JobDispatcher()


async def dispatch_job(
    user_id: UUID,
    tenant_id: UUID,
    job_type: JobType,
    input_data: dict[str, Any] | None = None,
    project_id: UUID | None = None,
) -> Job:
    return await job_dispatcher.dispatch(
        user_id=user_id,
        tenant_id=tenant_id,
        job_type=job_type,
        input_data=input_data,
        project_id=project_id,
    )


__all__ = [
    "JobDispatcher",
    "WorkerRoute",
    "dispatch_job",
    "job_dispatcher",
    "resolve_worker_route",
]
