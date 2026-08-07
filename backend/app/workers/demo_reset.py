"""M7 演示数据复位 Worker（Phase 4 验收项）。

由 L0 演示复位脚本 ``scripts/reset-demo.sh / .ps1`` 调用。
本 Worker 不导入业务表，仅返回操作摘要；
真正的 DB 复位由 L0/L4 提供的脚本完成（沙箱内只读）。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.workers.base import M7Task
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class DemoResetTask(M7Task):
    """演示数据复位任务占位。"""

    name = "app.workers.demo_reset.run"
    scene = "demo_reset"
    prompt_name = "demo_reset"
    prompt_version = "1.0.0"

    def run(self, scope: str = "demo") -> dict[str, Any]:
        timestamp = datetime.now(UTC).isoformat()
        logger.info("m7.demo_reset.tick scope=%s ts=%s", scope, timestamp)
        return {
            "jobId": "demo-reset",
            "status": "succeeded",
            "providerUsed": "offline",
            "output": {
                "scope": scope,
                "resetAt": timestamp,
                "ok": True,
                "note": "M7 仅占位；DB 复位由 L0 脚本执行",
            },
            "promptVersions": [],
            "tokenUsage": {"prompt": 0, "completion": 0, "total": 0},
            "errorCode": None,
            "errorMessage": None,
            "completedAt": timestamp,
        }


celery_app.tasks.register(DemoResetTask())


@celery_app.task(name="app.workers.demo_reset.run", bind=True, base=DemoResetTask)  # type: ignore[misc]
def run_demo_reset(self: DemoResetTask, scope: str = "demo") -> dict[str, Any]:
    return self.run(scope=scope)


__all__ = ["DemoResetTask", "run_demo_reset"]
