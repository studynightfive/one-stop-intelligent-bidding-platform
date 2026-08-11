"""End-to-end closure for eager tender parsing and bid review jobs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domains.bids.ports import JobRefSnapshot

from .conftest import BidHttpHarness


class _SucceededParseJob:
    async def enqueue(self, **kwargs: Any) -> JobRefSnapshot:
        job_id = "job-eager-parse"
        return JobRefSnapshot(
            id=job_id,
            type=str(kwargs["job_type"]),
            status="succeeded",
            progress_percent=100,
            created_at=datetime.now(UTC),
            current_step="招标文件解析完成",
            result={
                "jobId": job_id,
                "status": "succeeded",
                "providerUsed": "offline",
                "output": {
                    "summary": "已识别招标范围、评分规则和响应材料。",
                    "parsedSections": [
                        {"index": 0, "title": "项目概况", "wordCount": 120},
                        {"index": 1, "title": "技术要求", "wordCount": 360},
                    ],
                },
            },
        )


class _SucceededReviewJob:
    async def enqueue(self, **kwargs: Any) -> JobRefSnapshot:
        job_id = "job-eager-review"
        return JobRefSnapshot(
            id=job_id,
            type=str(kwargs["job_type"]),
            status="succeeded",
            progress_percent=100,
            created_at=datetime.now(UTC),
            current_step="投标审核完成",
            result={
                "jobId": job_id,
                "status": "succeeded",
                "providerUsed": "offline",
                "output": {
                    "summary": "离线审核完成，请人工确认关键结论。",
                    "findings": [
                        {
                            "type": "content",
                            "severity": "info",
                            "title": "人工复核提示",
                            "description": "当前使用离线模型结果。",
                            "suggestion": "启用生产模型后再次审核。",
                        }
                    ],
                },
            },
        )


def test_eager_parse_and_review_results_are_applied_automatically(bid_http: BidHttpHarness) -> None:
    task = bid_http.create_task("解析审核闭环项目")
    task_id = str(task["id"])

    bid_http.container.bids.jobs = _SucceededParseJob()
    parsed = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/parse",
        headers={"Idempotency-Key": "eager-parse"},
    )

    assert parsed.status_code == 202, parsed.text
    assert parsed.json()["data"]["status"] == "succeeded"
    parsed_task = bid_http.container.store.get_task(task_id, tenant_id="tenant-a")
    assert parsed_task.status == "material_prep"
    assert parsed_task.requirements is not None
    assert parsed_task.requirements.project_info["parsedSectionCount"] == "2"
    assert len(parsed_task.materials) == 6

    bid_http.container.bids.jobs = _SucceededReviewJob()
    reviewed = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/reviews",
        headers={"Idempotency-Key": "eager-review"},
        json={"types": ["signature", "price", "content", "consistency"]},
    )

    assert reviewed.status_code == 202, reviewed.text
    assert reviewed.json()["data"]["status"] == "succeeded"
    report_response = bid_http.client.get(f"/api/v1/bid-tasks/{task_id}/reviews/latest")
    assert report_response.status_code == 200, report_response.text
    report = report_response.json()["data"]
    assert report["status"] == "succeeded"
    assert report["summary"] == "离线审核完成，请人工确认关键结论。"
    assert report["findings"][0]["fileId"] == parsed_task.tender_file_id
    assert report["findings"][0]["decision"] == "pending"
