"""Job reference mapping stays aligned with the shared OpenAPI contract."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domains.evaluations.mappers import job_ref_dict
from app.domains.evaluations.ports import JobRefSnapshot


def test_job_ref_includes_optional_result_and_error() -> None:
    succeeded = JobRefSnapshot(
        id="job-1",
        type="report_generate",
        status="succeeded",
        progress_percent=100,
        created_at=datetime(2026, 8, 10, tzinfo=UTC),
        current_step="completed",
        result={"reportId": "report-1"},
    )
    failed = JobRefSnapshot(
        id="job-2",
        type="evaluation_score",
        status="failed",
        progress_percent=40,
        created_at=datetime(2026, 8, 10, tzinfo=UTC),
        error={"code": "AI_PROVIDER_UNAVAILABLE", "message": "模型暂不可用", "retryable": True},
    )

    assert job_ref_dict(succeeded)["result"] == {"reportId": "report-1"}
    assert "error" not in job_ref_dict(succeeded)
    assert job_ref_dict(failed)["error"]["retryable"] is True
    assert "result" not in job_ref_dict(failed)
