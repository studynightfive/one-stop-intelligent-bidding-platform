"""Celery 应用实例。

启动命令::

    celery -A app.workers.celery_app worker --loglevel=INFO
    celery -A app.workers.celery_app beat   --loglevel=INFO
    celery -A app.workers.celery_app flower --port=5555

本模块：
- 注册 Worker 配置（broker / backend / 队列 / 限流）；
- 注册 Worker 基类 ``M7Task``（统一进度、取消、幂等、重试）；
- 注册 Phase 0/1 占位任务（心跳、no-op）；
- 注册 Phase 2/3 任务（投标解析/匹配/审核/生成 + 评标完整性/风险/评分/报告）。

注意：本模块不导入 M5/M6 业务模块，避免循环依赖。
"""

from __future__ import annotations

import logging

from celery import Celery  # type: ignore[import-untyped]
from celery.schedules import schedule  # type: ignore[import-untyped]

from app.workers.settings import WorkerSettings, get_worker_settings

logger = logging.getLogger(__name__)


def _build_celery(settings: WorkerSettings) -> Celery:
    app = Celery(
        "m7_workers",
        broker=settings.broker_url,
        backend=settings.result_backend,
        include=[
            "app.workers.heartbeat",
            "app.workers.demo_reset",
            "app.workers.bidding_parser",
            "app.workers.bidding_matcher",
            "app.workers.bidding_auditor",
            "app.workers.bidding_generator",
            "app.workers.eval_integrity",
            "app.workers.eval_risk",
            "app.workers.eval_scorer",
            "app.workers.eval_reporter",
        ],
    )

    app.conf.update(
        task_default_queue=settings.task_default_queue,
        task_acks_late=settings.task_acks_late,
        task_reject_on_worker_lost=settings.task_reject_on_worker_lost,
        task_soft_time_limit=settings.task_soft_time_limit_seconds,
        task_time_limit=settings.task_hard_time_limit_seconds,
        broker_transport_options={
            "visibility_timeout": settings.visibility_timeout_seconds,
            "global_keyprefix": f"{settings.key_prefix}:celery:",
        },
        result_backend_transport_options={
            "global_keyprefix": f"{settings.key_prefix}:celery-results:",
        },
        worker_max_tasks_per_child=settings.worker_max_tasks_per_child,
        worker_prefetch_multiplier=settings.worker_prefetch_multiplier,
        task_always_eager=settings.eager_mode,
        task_eager_propagates=settings.eager_mode,
        timezone="UTC",
        enable_utc=True,
    )

    # Beat 调度：心跳任务用于 Phase 1 健康检查 + 后续演示复位。
    app.conf.beat_schedule = {
        "m7-heartbeat-every-minute": {
            "task": "app.workers.heartbeat.record_heartbeat",
            "schedule": schedule(run_every=60.0),
        },
    }

    return app


def build_celery_app(settings: WorkerSettings | None = None) -> Celery:
    """构造 Celery 应用，便于测试复用。"""

    return _build_celery(settings or get_worker_settings())


celery_app = build_celery_app()


__all__ = ["build_celery_app", "celery_app"]
