"""Celery 应用配置测试。"""

from __future__ import annotations

import pytest

# 在模块级别导入，确保 Celery Task 自动注册副作用被触发。
import app.workers.bidding_auditor
import app.workers.bidding_generator
import app.workers.bidding_matcher
import app.workers.bidding_parser
import app.workers.demo_reset
import app.workers.eval_integrity
import app.workers.eval_reporter
import app.workers.eval_risk
import app.workers.eval_scorer
import app.workers.heartbeat  # noqa: F401
from app.workers.celery_app import celery_app
from app.workers.settings import WorkerSettings


def test_celery_app_basic_config() -> None:
    assert celery_app.main == "m7_workers"
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.task_acks_late is True


def test_celery_app_includes_workers_in_beat_schedule() -> None:
    schedule = celery_app.conf.beat_schedule or {}
    assert "m7-heartbeat-every-minute" in schedule


def test_worker_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/1")
    monkeypatch.setenv("WORKER_DEFAULT_QUEUE", "m7_test")
    monkeypatch.setenv("WORKER_SOFT_TIME_LIMIT", "30")
    settings = WorkerSettings.from_env()
    assert settings.broker_url == "redis://redis:6379/1"
    assert settings.task_default_queue == "m7_test"
    assert settings.task_soft_time_limit_seconds == 30


def test_celery_tasks_registered() -> None:
    """所有业务 Task 已在 celery_app 注册（前提是 import 触发）。"""
    names = {k for k in celery_app.tasks if k.startswith("app.workers.")}
    assert names == {
        "app.workers.heartbeat.record_heartbeat",
        "app.workers.demo_reset.run",
        "app.workers.bidding_parser.parse",
        "app.workers.bidding_matcher.match",
        "app.workers.bidding_auditor.review",
        "app.workers.bidding_generator.generate",
        "app.workers.eval_integrity.check",
        "app.workers.eval_risk.check",
        "app.workers.eval_scorer.score",
        "app.workers.eval_reporter.generate",
    }
