"""M5 state-machine recovery and M7 JobResult write-back tests."""

from __future__ import annotations

import asyncio
from hashlib import sha256

import pytest

from app.contracts.generated.models import BidDocument, BidReviewFinding, BidReviewReport, DocumentVersion
from app.domains.bids.binary import make_docx_bytes
from app.domains.bids.enums import (
    JOB_TYPE_DOCUMENT_GENERATE,
    JOB_TYPE_MATERIAL_MATCH,
    JOB_TYPE_REVIEW,
    JOB_TYPE_TEMPLATE_GENERATE,
    JOB_TYPE_TENDER_PARSE,
)
from app.domains.bids.errors import DomainError
from app.domains.bids.ports import FileRefSnapshot
from app.domains.bids.state_machine import TRANSITIONS, assert_transition

from .conftest import BidHttpHarness


def test_state_machine_matches_m5_spec_and_failed_parse_can_retry(bid_http: BidHttpHarness) -> None:
    assert {
        "draft": {"parsing", "failed"},
        "parsing": {"material_prep", "failed"},
        "material_prep": {"ai_review", "failed"},
        "ai_review": {"pending_output", "failed"},
        "pending_output": {"completed", "failed"},
        "completed": {"archived"},
        "archived": set(),
        "failed": {"parsing", "material_prep", "ai_review", "pending_output"},
    } == TRANSITIONS
    for current, allowed in TRANSITIONS.items():
        for target in TRANSITIONS:
            if target in allowed:
                assert_transition(current, target)
            else:
                with pytest.raises(DomainError) as exc_info:
                    assert_transition(current, target)
                assert exc_info.value.code == "INVALID_STATE_TRANSITION"
                assert exc_info.value.details["currentStatus"] == current
                assert "allowedActions" in exc_info.value.details
    task = bid_http.create_task("状态机任务")
    path = f"/api/v1/bid-tasks/{task['id']}/parse"
    first = bid_http.client.post(path, headers={"Idempotency-Key": "parse-state-1"})
    assert first.status_code == 202

    illegal = bid_http.client.post(path, headers={"Idempotency-Key": "parse-state-2"})
    assert illegal.status_code == 409
    assert illegal.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
    assert illegal.json()["error"]["details"]["currentStatus"] == "parsing"

    failed = asyncio.run(
        bid_http.container.bids.apply_job_failure(
            tenant_id="tenant-a",
            task_id=str(task["id"]),
            job_id=str(first.json()["data"]["id"]),
            failed_stage="parsing",
            message="解析器失败",
        )
    )
    assert failed["status"] == "failed"
    wrong_stage = bid_http.client.post(
        f"/api/v1/bid-tasks/{task['id']}/reviews",
        headers={"Idempotency-Key": "wrong-stage-review"},
        json={"types": ["content"]},
    )
    assert wrong_stage.status_code == 409
    assert wrong_stage.json()["error"]["code"] == "CONFLICT"
    retry = bid_http.client.post(path, headers={"Idempotency-Key": "parse-state-3"})
    assert retry.status_code == 202
    assert bid_http.container.store.get_task(str(task["id"]), tenant_id="tenant-a").status == "parsing"


def test_job_results_write_back_once_and_document_rollback_preserves_history(
    bid_http: BidHttpHarness,
) -> None:
    task = bid_http.create_task("异步闭环项目")
    task_id = str(task["id"])
    parse_job = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/parse",
        headers={"Idempotency-Key": "parse-flow-key"},
    ).json()["data"]

    parse_result = asyncio.run(
        bid_http.container.bids.apply_parse_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=str(parse_job["id"]),
            requirements={
                "projectInfo": {"budgetAmount": "100000.00"},
                "scoringItems": [{"name": "技术", "score": "60", "basis": "招标文件"}],
                "disqualificationItems": [{"name": "签章", "basis": "招标文件"}],
                "qualificationRequirements": ["营业执照"],
                "technicalRequirements": ["技术方案"],
            },
            materials=[
                {
                    "name": "技术方案",
                    "category": "technical",
                    "requirement": "完整响应",
                    "required": True,
                    "sortOrder": 0,
                }
            ],
        )
    )
    repeated_parse = asyncio.run(
        bid_http.container.bids.apply_parse_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=str(parse_job["id"]),
            requirements={},
            materials=[],
        )
    )
    assert repeated_parse == parse_result
    assert len(bid_http.container.store.materials) == 1
    assert bid_http.container.store.get_task(task_id, tenant_id="tenant-a").status == "material_prep"

    review_job = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/reviews",
        headers={"Idempotency-Key": "review-flow-key"},
        json={"types": ["content"]},
    )
    assert review_job.status_code == 202, review_job.text
    review_job_id = str(review_job.json()["data"]["id"])
    review = asyncio.run(
        bid_http.container.bids.apply_review_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=review_job_id,
            summary="发现一项高风险",
            findings=[
                {
                    "type": "content",
                    "severity": "high",
                    "title": "缺少响应",
                    "description": "技术响应不完整",
                    "fileId": "tender-1",
                    "page": 1,
                    "suggestion": "补充内容",
                }
            ],
        )
    )
    repeated_review = asyncio.run(
        bid_http.container.bids.apply_review_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=review_job_id,
            summary="不应覆盖",
            findings=[],
        )
    )
    assert repeated_review == review
    BidReviewReport.model_validate(review)
    assert review["status"] == "succeeded"
    assert len(review["findings"]) == 1
    finding_id = str(review["findings"][0]["id"])
    decided = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/review-findings/{finding_id}/decision",
        json={"decision": "accepted", "comment": "已人工确认"},
    )
    assert decided.status_code == 200, decided.text
    BidReviewFinding.model_validate(decided.json()["data"])

    document_job = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/documents",
        headers={"Idempotency-Key": "document-flow-key"},
        json={
            "mode": "split",
            "sections": ["technical"],
            "templateMode": "standard",
            "includeWatermark": False,
        },
    )
    assert document_job.status_code == 202, document_job.text
    document_job_id = str(document_job.json()["data"]["id"])
    content = make_docx_bytes(sections=["technical"], project_name="异步闭环项目")
    digest = sha256(content).hexdigest()
    assert bid_http.container.ports is not None
    bid_http.container.ports.files["generated-doc"] = FileRefSnapshot(
        id="generated-doc",
        file_name="technical.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=len(content),
        sha256=digest,
        scan_status="clean",
        created_at=bid_http.container.ports.files["tender-1"].created_at,
    )
    with pytest.raises(DomainError, match="原始任务"):
        asyncio.run(
            bid_http.container.bids.apply_document_result(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=document_job_id,
                files=[
                    {
                        "type": "technical",
                        "fileId": "generated-doc",
                        "content": content,
                    }
                ],
                actor_id="user-owner",
                actor_name="伪造执行人",
            )
        )
    assert bid_http.container.document_store.versions == {}
    documents = asyncio.run(
        bid_http.container.bids.apply_document_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=document_job_id,
            files=[
                {
                    "type": "technical",
                    "fileId": "generated-doc",
                    "content": content,
                    "textContent": "## 技术方案\n第一版方案",
                    "changeSummary": "生成技术标",
                }
            ],
            actor_id="user-owner",
            actor_name="负责人",
        )
    )
    repeated_documents = asyncio.run(
        bid_http.container.bids.apply_document_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=document_job_id,
            files=[],
            actor_id="user-owner",
            actor_name="负责人",
        )
    )
    assert repeated_documents == documents
    for document in documents:
        BidDocument.model_validate(document)
    assert len(bid_http.container.document_store.versions) == 1
    assert bid_http.container.store.get_task(task_id, tenant_id="tenant-a").status == "completed"

    document_id = str(documents[0]["id"])
    download = bid_http.client.get(f"/api/v1/bid-tasks/{task_id}/documents/{document_id}/download")
    assert download.status_code == 200
    assert download.content == content
    assert download.headers["X-File-Sha256"] == digest

    first_version = next(iter(bid_http.container.document_store.versions.values()))
    rollback = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/document-versions/{first_version.id}/rollback",
        headers={"Idempotency-Key": "rollback-flow-key"},
        json={"reason": "恢复首版"},
    )
    repeated_rollback = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/document-versions/{first_version.id}/rollback",
        headers={"Idempotency-Key": "rollback-flow-key"},
        json={"reason": "恢复首版"},
    )
    assert rollback.status_code == repeated_rollback.status_code == 202
    assert rollback.json()["data"] == repeated_rollback.json()["data"]

    rollback_job_id = str(rollback.json()["data"]["id"])
    with pytest.raises(DomainError, match="原始任务输入"):
        asyncio.run(
            bid_http.container.bids.apply_document_rollback_result(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=rollback_job_id,
                target_version_id=first_version.id,
                reason="被篡改的原因",
                actor_id="user-owner",
                actor_name="负责人",
            )
        )
    assert len(bid_http.container.document_store.versions) == 1
    rolled_back = asyncio.run(
        bid_http.container.bids.apply_document_rollback_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=rollback_job_id,
            target_version_id=first_version.id,
            reason="恢复首版",
            actor_id="user-owner",
            actor_name="负责人",
        )
    )
    repeated_result = asyncio.run(
        bid_http.container.bids.apply_document_rollback_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=rollback_job_id,
            target_version_id=first_version.id,
            reason="重复结果不得创建版本",
            actor_id="user-owner",
            actor_name="负责人",
        )
    )
    assert repeated_result == rolled_back
    DocumentVersion.model_validate(rolled_back)
    assert rolled_back["versionNumber"] == 2
    assert len(bid_http.container.document_store.versions) == 2
    latest = max(bid_http.container.document_store.versions.values(), key=lambda item: item.version_number)
    assert latest.roll_back is True
    assert latest.source_version_id == first_version.id
    assert latest.content == content
    assert latest.sha256 == digest

    failed_rollback_job = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/document-versions/{first_version.id}/rollback",
        headers={"Idempotency-Key": "rollback-flow-failure-key"},
        json={"reason": "测试失败回写"},
    ).json()["data"]
    failed_rollback_job_id = str(failed_rollback_job["id"])
    failure = asyncio.run(
        bid_http.container.bids.apply_job_failure(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=failed_rollback_job_id,
            failed_stage="pending_output",
            message="回滚 Worker 失败",
        )
    )
    repeated_failure = asyncio.run(
        bid_http.container.bids.apply_job_failure(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=failed_rollback_job_id,
            failed_stage="pending_output",
            message="重复失败不得再次副作用",
        )
    )
    assert repeated_failure == failure
    assert failure["status"] == "completed"
    assert len(bid_http.container.document_store.versions) == 2

    with pytest.raises(DomainError, match="相反的终态结果"):
        asyncio.run(
            bid_http.container.bids.apply_document_rollback_result(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=failed_rollback_job_id,
                target_version_id=first_version.id,
                reason="失败后不得再接受成功回写",
                actor_id="user-owner",
                actor_name="负责人",
            )
        )


def test_every_lifecycle_async_failure_is_validated_and_idempotent(bid_http: BidHttpHarness) -> None:
    cases = (
        ("parsing", JOB_TYPE_TENDER_PARSE),
        ("material_prep", JOB_TYPE_MATERIAL_MATCH),
        ("material_prep", JOB_TYPE_TEMPLATE_GENERATE),
        ("ai_review", JOB_TYPE_REVIEW),
        ("pending_output", JOB_TYPE_DOCUMENT_GENERATE),
    )

    for index, (stage, action) in enumerate(cases):
        task = bid_http.create_task(f"异步失败-{index}")
        task_id = str(task["id"])
        stored = bid_http.container.store.get_task(task_id, tenant_id="tenant-a")
        stored.status = stage
        bid_http.container.store.save_task(stored)
        job_id = f"failure-job-{index}"
        bid_http.container.store.remember_job(
            job_id,
            tenant_id="tenant-a",
            task_id=task_id,
            action=action,
        )

        first = asyncio.run(
            bid_http.container.bids.apply_job_failure(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=job_id,
                failed_stage=stage,
                message="Worker 失败",
            )
        )
        repeated = asyncio.run(
            bid_http.container.bids.apply_job_failure(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=job_id,
                failed_stage=stage,
                message="重复失败结果",
            )
        )
        assert repeated == first
        assert first["status"] == "failed"

    assert bid_http.container.ports is not None
    assert len(bid_http.container.ports.notifications) == len(cases)
