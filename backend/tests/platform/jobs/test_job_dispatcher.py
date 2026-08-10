"""Platform job dispatcher integration tests."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.domains.jobs.services.job_dispatcher as dispatcher_module
from app.domains.jobs.models.job import JobStatus, JobType
from app.domains.jobs.services.job_dispatcher import JobDispatcher, resolve_worker_route
from app.domains.jobs.services.job_service import JobService


def test_resolve_worker_route_covers_m5_and_m6_scenes() -> None:
    bid_route = resolve_worker_route({"m5JobType": "bid.document_generate"})
    evaluation_route = resolve_worker_route({"m6JobType": "evaluation.ai_scoring"})

    assert bid_route is not None
    assert bid_route.task_name == "app.workers.bidding_generator.generate"
    assert evaluation_route is not None
    assert evaluation_route.task_name == "app.workers.eval_scorer.score"
    assert resolve_worker_route({"m5JobType": "bid.document_rollback"}) is None


@pytest.mark.asyncio
async def test_eager_dispatch_runs_worker_and_persists_result(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.workers.celery_app import celery_app

    @asynccontextmanager
    async def test_db_context():
        yield db_session

    monkeypatch.setattr(dispatcher_module, "get_db_context", test_db_context)
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)
    monkeypatch.setenv("REDIS_URL", "")

    dispatcher = JobDispatcher(celery_app)
    job = await dispatcher.dispatch(
        user_id=uuid4(),
        tenant_id=uuid4(),
        job_type=JobType.DOCUMENT_GENERATION,
        input_data={
            "m5JobType": "bid.document_generate",
            "projectInfo": {},
            "library": [],
            "mode": "split",
        },
    )

    assert job.status == JobStatus.SUCCEEDED
    assert job.progress_percent == 100
    assert job.celery_task_id == str(job.id)
    assert job.result is not None
    assert job.result["status"] == "succeeded"
    assert "outline" in job.result["output"]


@pytest.mark.asyncio
async def test_refresh_persists_async_worker_success(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @asynccontextmanager
    async def test_db_context():
        yield db_session

    class CompletedResult:
        state = "SUCCESS"
        result = {
            "jobId": "worker-job",
            "status": "succeeded",
            "output": {"ok": True},
            "promptVersions": [],
            "tokenUsage": {"prompt": 0, "completion": 0, "total": 0},
        }

    class FakeCelery:
        def AsyncResult(self, task_id: str) -> CompletedResult:  # noqa: N802
            assert task_id == "celery-task-1"
            return CompletedResult()

    monkeypatch.setattr(dispatcher_module, "get_db_context", test_db_context)
    service = JobService(db_session)
    job = await service.create_job(
        user_id=uuid4(),
        tenant_id=uuid4(),
        job_type=JobType.AI_ANALYSIS,
    )
    await service.bind_celery_task_id(job.id, "celery-task-1")

    refreshed = await JobDispatcher(FakeCelery()).refresh(job.id)

    assert refreshed is not None
    assert refreshed.status == JobStatus.SUCCEEDED
    assert refreshed.result is not None
    assert refreshed.result["output"] == {"ok": True}


@pytest.mark.asyncio
async def test_eager_dispatch_rejects_invalid_worker_result(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @asynccontextmanager
    async def test_db_context():
        yield db_session

    class EagerResult:
        id = "celery-invalid"

        def get(self, *, propagate: bool) -> str:
            assert propagate is False
            return "not-an-object"

    class FakeTask:
        def apply(self, *, args: list[Any], task_id: str) -> EagerResult:
            assert args
            assert task_id
            return EagerResult()

    class Conf:
        task_always_eager = True

    class FakeCelery:
        conf = Conf()
        tasks = {"app.workers.bidding_generator.generate": FakeTask()}

        def register_task(self, task: FakeTask) -> FakeTask:
            return task

    monkeypatch.setattr(dispatcher_module, "get_db_context", test_db_context)
    monkeypatch.setattr(dispatcher_module.importlib, "import_module", lambda name: None)
    job = await JobDispatcher(FakeCelery()).dispatch(
        user_id=uuid4(),
        tenant_id=uuid4(),
        job_type=JobType.DOCUMENT_GENERATION,
        input_data={"m5JobType": "bid.document_generate"},
    )

    assert job.status == JobStatus.FAILED
    assert job.error is not None
    assert job.error["code"] == "INVALID_WORKER_RESULT"
