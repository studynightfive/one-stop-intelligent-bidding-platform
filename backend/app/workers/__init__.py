"""M7 Celery Worker 包。

负责：
- Celery 实例与 Beat 调度；
- Worker 任务统一基类（进度、取消、幂等、死信）；
- 业务无关的占位任务（心跳、no-op），Phase 0 启动可达；
- Phase 2/3 由 M7 接入 M5/M6 后扩展。

本包不导入 M5/M6 业务 ORM；所有数据经 ``JobResult`` 返回，
由 M5/M6 业务 service 校验后落库。
"""

from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.settings import WorkerSettings, get_worker_settings

__all__ = [
    "WorkerSettings",
    "celery_app",
    "get_worker_settings",
]
