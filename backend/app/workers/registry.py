"""Task 注册辅助。

集中注册所有业务 Worker Task，供 ``celery_app`` 与单元测试共用。
"""

from __future__ import annotations

from collections.abc import Iterable

from app.workers.celery_app import celery_app


def register_task(task: object) -> None:
    """注册单个 Task 实例到 Celery。"""

    celery_app.tasks.register(task)


def register_all(task_classes: Iterable[type]) -> None:
    """把所有 Task 类实例化并注册。"""

    for cls in task_classes:
        celery_app.tasks.register(cls())


__all__ = ["register_all", "register_task"]
