"""M5 投标解析 Worker（Phase 2）。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.ai.router import invoke
from app.ai.schemas import (
    JobResult,
    JobSpec,
    JobStatus,
    ProviderStatus,
)
from app.workers.base import M7Task, run_task_handler

logger = logging.getLogger(__name__)


class BiddingParserTask(M7Task):
    """招标文件解析：把 PDF/Word 文本拆为 Markdown 章节 + 元数据。"""

    name = "app.workers.bidding_parser.parse"
    scene = "tender_parse"
    prompt_name = "tender_parse"
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
                output={
                    "parsedSections": structured.get("sections", []),
                    "summary": structured.get("summary", ""),
                },
                prompt_versions=prompt_versions,
                token_usage=token_usage,
                error_code="AI_PROVIDER_UNAVAILABLE",
                error_message="provider unavailable, fallback to offline mode",
            )
        return JobResult(
            job_id=spec.job_id,
            status=JobStatus.SUCCEEDED,
            provider_used=output.provider_status,
            output={
                "parsedSections": structured.get("sections", []),
                "summary": structured.get("summary", ""),
            },
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


__all__ = ["BiddingParserTask"]


# 注册到 Celery（启动时一次性副作用）。
from app.workers.registry import register_task as _register_task  # noqa: E402

_register_task(BiddingParserTask())
