"""M5 eager-result closure for paragraph-generated technical DOCX files."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from app.domains.bids.ports import JobRefSnapshot
from app.domains.documents.docx import extract_docx_text

from .conftest import BidHttpHarness


class _SucceededTechnicalDocumentJob:
    def __init__(self) -> None:
        self.payload: dict[str, Any] | None = None

    async def enqueue(self, **kwargs: Any) -> JobRefSnapshot:
        self.payload = dict(kwargs["payload"])
        job_id = "job-eager-technical-document"
        return JobRefSnapshot(
            id=job_id,
            type="document_generation",
            status="succeeded",
            progress_percent=100,
            created_at=datetime.now(UTC),
            current_step="技术文档生成完成",
            result={
                "jobId": job_id,
                "status": "succeeded",
                "providerUsed": "primary",
                "output": {
                    "outline": [
                        {
                            "section": "1 总体技术方案",
                            "sectionKey": "overall",
                            "headingLevel": 1,
                            "estimatedWords": 360,
                        }
                    ],
                    "technicalDocument": {
                        "strategy": "paragraph_by_paragraph",
                        "templateName": "技术标标准模板",
                        "status": "completed",
                        "sections": [
                            {
                                "key": "overall",
                                "heading": "1 总体技术方案",
                                "headingLevel": 1,
                                "paragraphs": [
                                    {
                                        "index": 1,
                                        "text": "第一段说明总体架构与实施边界。",
                                        "evidence": [{"sourceId": "REQ-01", "summary": "招标技术要求"}],
                                    },
                                    {
                                        "index": 2,
                                        "text": "第二段说明质量控制与验收方法。",
                                        "evidence": [{"sourceId": "REQ-02", "summary": "项目验收要求"}],
                                    },
                                ],
                                "images": [],
                            }
                        ],
                        "referenceImages": [],
                    },
                },
                "promptVersions": [],
                "tokenUsage": {"prompt": 20, "completion": 40, "total": 60},
                "errorCode": None,
                "errorMessage": None,
            },
        )


def _prepare_successful_review(bid_http: BidHttpHarness, task_id: str) -> None:
    task = bid_http.container.store.get_task(task_id, tenant_id="tenant-a")
    task.status = "material_prep"
    bid_http.container.store.save_task(task)
    review = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/reviews",
        headers={"Idempotency-Key": "review-before-eager-document"},
        json={"types": ["content"]},
    )
    assert review.status_code == 202, review.text
    asyncio.run(
        bid_http.container.bids.apply_review_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=str(review.json()["data"]["id"]),
            summary="审核通过",
            findings=[],
        )
    )


def test_eager_worker_result_is_assembled_versioned_and_downloadable(bid_http: BidHttpHarness) -> None:
    task = bid_http.create_task("AI 技术文档项目")
    task_id = str(task["id"])
    _prepare_successful_review(bid_http, task_id)
    eager_jobs = _SucceededTechnicalDocumentJob()
    bid_http.container.bids.jobs = eager_jobs
    technical_document = {
        "strategy": "paragraph_by_paragraph",
        "templateName": "技术标标准模板",
        "sections": [
            {
                "key": "overall",
                "heading": "1 总体技术方案",
                "headingLevel": 1,
                "instructions": "说明总体架构和实施边界。",
                "targetParagraphs": 2,
                "targetWordsPerParagraph": 180,
                "required": True,
            }
        ],
        "referenceImages": [],
        "contextWindowCharacters": 2_000,
        "carryForwardParagraphs": 2,
        "preserveHeadingNumbering": True,
        "requireEvidence": True,
    }

    response = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/documents",
        headers={"Idempotency-Key": "eager-technical-document"},
        json={
            "mode": "split",
            "sections": ["technical"],
            "templateMode": "standard",
            "includeWatermark": True,
            "technicalDocument": technical_document,
        },
    )

    assert response.status_code == 202, response.text
    assert eager_jobs.payload is not None
    assert eager_jobs.payload["technicalDocument"] == technical_document
    assert eager_jobs.payload["projectInfo"]["projectName"] == "AI 技术文档项目"
    assert "requirements" in eager_jobs.payload
    assert "library" in eager_jobs.payload
    assert bid_http.container.store.get_task(task_id, tenant_id="tenant-a").status == "completed"

    documents = bid_http.client.get(f"/api/v1/bid-tasks/{task_id}/documents")
    assert documents.status_code == 200, documents.text
    item = documents.json()["data"][0]
    assert item["type"] == "technical"
    download = bid_http.client.get(f"/api/v1/bid-tasks/{task_id}/documents/{item['id']}/download")
    assert download.status_code == 200
    text = extract_docx_text(download.content)
    assert "第一段说明总体架构与实施边界" in text
    assert "第二段说明质量控制与验收方法" in text
    assert "依据：REQ-01 - 招标技术要求" in text


def test_technical_document_requires_technical_section(bid_http: BidHttpHarness) -> None:
    task = bid_http.create_task("非法技术文档请求")
    task_id = str(task["id"])
    _prepare_successful_review(bid_http, task_id)
    response = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/documents",
        headers={"Idempotency-Key": "invalid-technical-document"},
        json={
            "mode": "split",
            "sections": ["commercial"],
            "templateMode": "standard",
            "includeWatermark": False,
            "technicalDocument": {
                "strategy": "paragraph_by_paragraph",
                "templateName": "技术模板",
                "sections": [
                    {
                        "key": "technical",
                        "heading": "技术方案",
                        "headingLevel": 1,
                        "instructions": "生成技术方案。",
                        "targetParagraphs": 1,
                        "targetWordsPerParagraph": 100,
                        "required": True,
                    }
                ],
                "referenceImages": [],
                "contextWindowCharacters": 2_000,
                "carryForwardParagraphs": 1,
                "preserveHeadingNumbering": True,
                "requireEvidence": False,
            },
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["fieldErrors"][0]["code"] == "MISSING_TECHNICAL_SECTION"
