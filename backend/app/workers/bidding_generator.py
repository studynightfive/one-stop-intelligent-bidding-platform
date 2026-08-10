"""M5 投标生成 Worker（Phase 2）。"""

from __future__ import annotations

import asyncio
from typing import Any

from app.ai.router import invoke
from app.ai.schemas import (
    JobResult,
    JobSpec,
    JobStatus,
    ProviderStatus,
)
from app.workers.base import M7Task, run_task_handler


class BiddingGeneratorTask(M7Task):
    """摘要 / 标书结构 / 评分初稿。"""

    name = "app.workers.bidding_generator.generate"
    scene = "bid_generate"
    prompt_name = "bid_generate"
    prompt_version = "1.0.0"
    max_retries = 3

    async def _execute(self, spec: JobSpec, payload: dict[str, Any]) -> JobResult:
        output = await invoke(spec, payload=payload)
        prompt_versions = [output.prompt_version]
        token_usage = output.prompt_version.token_usage
        structured = output.structured or {}
        if output.provider_status == ProviderStatus.OFFLINE:
            return self.make_partial_result(
                job_id=spec.job_id,
                output={"outline": structured.get("outline", [])},
                prompt_versions=prompt_versions,
                token_usage=token_usage,
                error_code="AI_PROVIDER_UNAVAILABLE",
                error_message="provider unavailable, fallback to offline mode",
            )
        return JobResult(
            job_id=spec.job_id,
            status=JobStatus.SUCCEEDED,
            provider_used=output.provider_status,
            output={"outline": structured.get("outline", [])},
            prompt_versions=prompt_versions,
            token_usage=token_usage,
        )

    def execute(self, spec: JobSpec, payload: dict[str, Any]) -> JobResult:
        from typing import cast

        result = cast(JobResult, _run_async(self._execute(spec, payload)))
        return result

    def run(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return run_task_handler(self, lambda spec, data: self.execute(spec, dict(data)))(job_id, payload)


def _run_async(coro: Any) -> Any:  # noqa: ANN401
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        return asyncio.ensure_future(coro)
    return loop.run_until_complete(coro)


__all__ = ["BiddingGeneratorTask"]

# 注册到 Celery（启动时一次性副作用）。
from app.workers.registry import register_task as _register_task  # noqa: E402

_register_task(BiddingGeneratorTask())
