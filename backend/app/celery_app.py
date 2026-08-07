"""Celery 应用配置.

用于异步任务执行。
"""

from celery import Celery

from app.core.config import settings


def create_celery_app() -> Celery:
    """创建 Celery 应用实例.

    Returns:
        Celery 应用实例
    """
    celery_app = Celery(
        "bid_platform",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=[
            "app.domains.jobs.tasks",
        ],
    )

    # Celery 配置
    celery_app.conf.update(
        # 任务序列化
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Shanghai",
        enable_utc=True,

        # 任务路由
        task_routes={
            "app.domains.jobs.tasks.*": {"queue": "jobs"},
        },

        # 任务执行配置
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_time_limit=3600,  # 1小时
        task_soft_time_limit=3300,  # 55分钟

        # Worker 配置
        worker_prefetch_multiplier=1,
        worker_concurrency=4,

        # 结果存储
        result_expires=86400,  # 24小时
        result_backend_transport_options={
            "master_name": "mymaster",
        },

        # 定期任务
        beat_schedule={},
    )

    return celery_app


# 创建 Celery 应用
celery_app = create_celery_app()
