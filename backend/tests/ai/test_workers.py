"""Worker Task 测试。"""

from __future__ import annotations

import pytest

from app.workers.celery_app import celery_app


@pytest.fixture
def eager_celery(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_eager_propagates", True)


def test_heartbeat_returns_succeeded(eager_celery) -> None:
    # heartbeat registered on import
    import app.workers.heartbeat  # noqa: F401

    task = celery_app.tasks["app.workers.heartbeat.record_heartbeat"]
    result = task.apply().get()
    assert result["status"] == "succeeded"
    assert result["output"]["ok"] is True


def test_demo_reset_returns_succeeded(eager_celery) -> None:
    import app.workers.demo_reset  # noqa: F401

    task = celery_app.tasks["app.workers.demo_reset.run"]
    result = task.apply(args=["full"]).get()
    assert result["status"] == "succeeded"
    assert result["output"]["scope"] == "full"


def test_bidding_parser_returns_succeeded(eager_celery) -> None:
    import app.workers.bidding_parser  # noqa: F401

    task = celery_app.tasks["app.workers.bidding_parser.parse"]
    result = task.apply(args=["job-1", {"projectName": "Demo", "rawText": "Sample"}]).get()
    assert result["status"] == "succeeded"
    assert result["providerUsed"] in {"primary", "fallback", "offline"}
    assert "parsedSections" in result["output"]


def test_bidding_matcher_returns_succeeded(eager_celery) -> None:
    import app.workers.bidding_matcher  # noqa: F401

    task = celery_app.tasks["app.workers.bidding_matcher.match"]
    result = task.apply(args=["job-2", {"requirements": [], "qualifications": [], "fragments": []}]).get()
    assert result["status"] == "succeeded"
    assert "matches" in result["output"]


def test_bidding_auditor_returns_succeeded(eager_celery) -> None:
    import app.workers.bidding_auditor  # noqa: F401

    task = celery_app.tasks["app.workers.bidding_auditor.review"]
    result = task.apply(args=["job-3", {"reviewTypes": ["content"], "fileVersionIds": [], "materials": []}]).get()
    assert result["status"] == "succeeded"
    assert "findings" in result["output"]


def test_bidding_generator_returns_succeeded(eager_celery) -> None:
    import app.workers.bidding_generator  # noqa: F401

    task = celery_app.tasks["app.workers.bidding_generator.generate"]
    result = task.apply(args=["job-4", {"projectInfo": {}, "library": [], "mode": "split"}]).get()
    assert result["status"] == "succeeded"
    assert "outline" in result["output"]


def test_eval_integrity_returns_succeeded(eager_celery) -> None:
    import app.workers.eval_integrity  # noqa: F401

    task = celery_app.tasks["app.workers.eval_integrity.check"]
    result = task.apply(args=["job-5", {"evaluationId": "e1", "requiredMaterials": [], "submissions": []}]).get()
    assert result["status"] == "succeeded"
    assert "completeness" in result["output"]


def test_eval_risk_returns_succeeded(eager_celery) -> None:
    import app.workers.eval_risk  # noqa: F401

    task = celery_app.tasks["app.workers.eval_risk.check"]
    result = task.apply(args=["job-6", {"evaluationId": "e1", "suppliers": [], "history": []}]).get()
    assert result["status"] == "succeeded"
    assert "findings" in result["output"]


def test_eval_scorer_returns_succeeded(eager_celery) -> None:
    import app.workers.eval_scorer  # noqa: F401

    task = celery_app.tasks["app.workers.eval_scorer.score"]
    result = task.apply(args=["job-7", {"scoringCriteria": [{"name": "技术方案"}], "supplierResponse": {}}]).get()
    assert result["status"] == "succeeded"
    assert "scores" in result["output"]


def test_eval_reporter_returns_succeeded(eager_celery) -> None:
    import app.workers.eval_reporter  # noqa: F401

    task = celery_app.tasks["app.workers.eval_reporter.generate"]
    result = task.apply(args=["job-8", {"evaluationId": "e1", "ranking": [], "risks": []}]).get()
    assert result["status"] == "succeeded"
    assert "reportTitle" in result["output"]
