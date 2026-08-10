"""M7 心跳 / 占位 Worker。

用于 Phase 1 健康检查与 Phase 4 演示复位。
注册在 :mod:`app.workers.celery_app` 的 ``include`` 中。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.workers.base import M7Task  # type: ignore[unused-ignore]
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class HeartbeatTask(M7Task):
    """周期心跳任务；用于监控 / 演示复位判定。"""

    name = "app.workers.heartbeat.record_heartbeat"
    scene = "heartbeat"
    prompt_name = "heartbeat"
    prompt_version = "1.0.0"

    def run(self) -> dict[str, Any]:
        timestamp = datetime.now(UTC).isoformat()
        logger.info("m7.heartbeat.tick ts=%s", timestamp)
        return {
            "jobId": "heartbeat",
            "status": "succeeded",
            "providerUsed": "offline",
            "output": {"heartbeatAt": timestamp, "ok": True},
            "promptVersions": [],
            "tokenUsage": {"prompt": 0, "completion": 0, "total": 0},
            "errorCode": None,
            "errorMessage": None,
            "completedAt": timestamp,
        }


celery_app.tasks.register(HeartbeatTask())


@celery_app.task(name="app.workers.heartbeat.record_heartbeat", bind=True, base=HeartbeatTask)  # type: ignore[misc]
def record_heartbeat(self: HeartbeatTask) -> dict[str, Any]:
    return self.run()


__all__ = ["HeartbeatTask", "record_heartbeat"]
