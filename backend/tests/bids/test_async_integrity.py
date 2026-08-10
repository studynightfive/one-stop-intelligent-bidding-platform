"""M5 async binding, retry-stage and concurrent idempotency regressions."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.domains.bids.binary import make_docx_bytes
from app.domains.bids.enums import JOB_TYPE_MATERIAL_MATCH, JOB_TYPE_TEMPLATE_GENERATE
from app.domains.bids.errors import DomainError
from app.domains.bids.ids import new_id

from .conftest import BidHttpHarness


def _set_status(bid_http: BidHttpHarness, task_id: str, status: str) -> None:
    task = bid_http.container.store.get_task(task_id, tenant_id="tenant-a")
    task.status = status
    bid_http.container.store.save_task(task)


def _create_material(bid_http: BidHttpHarness, task_id: str, name: str) -> str:
    response = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/materials",
        json={
            "name": name,
            "category": "technical",
            "requirement": "完整响应",
            "required": True,
            "sortOrder": 0,
        },
    )
    assert response.status_code == 200, response.text
    return str(response.json()["data"]["id"])


def test_my_quick_filter_is_applied_to_stats_list_and_board(bid_http: BidHttpHarness) -> None:
    mine = bid_http.create_task("我的任务")
    other = bid_http.create_task("他人任务")
    other_task = bid_http.container.store.get_task(str(other["id"]), tenant_id="tenant-a")
    other_task.assignee_id = "user-other"
    other_task.assignee_name = "其他负责人"
    bid_http.container.store.save_task(other_task)

    stats = bid_http.client.get("/api/v1/bid-tasks/stats", params={"quickFilter": "my"})
    listing = bid_http.client.get("/api/v1/bid-tasks", params={"quickFilter": "my"})
    board = bid_http.client.get("/api/v1/bid-tasks/board", params={"quickFilter": "my"})

    assert stats.status_code == listing.status_code == board.status_code == 200
    assert stats.json()["data"]["total"] == 1
    assert listing.json()["meta"]["total"] == 1
    listed_ids = {str(item["id"]) for item in listing.json()["data"]}
    board_ids = {str(item["id"]) for column in board.json()["data"] for item in column["tasks"]}
    assert listed_ids == board_ids == {str(mine["id"])}


def test_document_generation_waits_for_successful_review(bid_http: BidHttpHarness) -> None:
    task = bid_http.create_task("审核门禁任务")
    task_id = str(task["id"])
    _set_status(bid_http, task_id, "material_prep")
    review = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/reviews",
        headers={"Idempotency-Key": "review-gate"},
        json={"types": ["content"]},
    )
    assert review.status_code == 202, review.text

    payload = {
        "mode": "split",
        "sections": ["technical"],
        "templateMode": "standard",
        "includeWatermark": False,
    }
    blocked = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/documents",
        headers={"Idempotency-Key": "document-before-review"},
        json=payload,
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "CONFLICT"

    asyncio.run(
        bid_http.container.bids.apply_review_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=str(review.json()["data"]["id"]),
            summary="审核通过",
            findings=[],
        )
    )
    allowed = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/documents",
        headers={"Idempotency-Key": "document-after-review"},
        json=payload,
    )
    assert allowed.status_code == 202, allowed.text


def test_document_generation_replays_same_key_blocks_new_key_and_preserves_success(
    bid_http: BidHttpHarness,
) -> None:
    task = bid_http.create_task("文档生成并发门禁")
    task_id = str(task["id"])
    _set_status(bid_http, task_id, "material_prep")
    review = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/reviews",
        headers={"Idempotency-Key": "document-gate-review"},
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
    payload = {
        "mode": "split",
        "sections": ["technical"],
        "templateMode": "standard",
        "includeWatermark": False,
    }
    path = f"/api/v1/bid-tasks/{task_id}/documents"
    first = bid_http.client.post(path, headers={"Idempotency-Key": "document-gate-first"}, json=payload)
    replay = bid_http.client.post(path, headers={"Idempotency-Key": "document-gate-first"}, json=payload)
    duplicate = bid_http.client.post(path, headers={"Idempotency-Key": "document-gate-second"}, json=payload)

    assert first.status_code == replay.status_code == 202
    assert first.json()["data"] == replay.json()["data"]
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "CONFLICT"
    assert bid_http.container.ports is not None
    assert sum(job.type == "document_generation" for job in bid_http.container.ports.jobs) == 1

    first_job_id = str(first.json()["data"]["id"])
    failed = asyncio.run(
        bid_http.container.bids.apply_job_failure(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=first_job_id,
            failed_stage="pending_output",
            message="首次生成失败",
        )
    )
    assert failed["status"] == "failed"
    retry = bid_http.client.post(path, headers={"Idempotency-Key": "document-gate-retry"}, json=payload)
    assert retry.status_code == 202, retry.text
    assert sum(job.type == "document_generation" for job in bid_http.container.ports.jobs) == 2

    content = make_docx_bytes(sections=["technical"], project_name="文档生成并发门禁")
    bid_http.add_file(
        "document-gate-output",
        file_name="technical.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=content,
    )
    retry_job_id = str(retry.json()["data"]["id"])
    documents = asyncio.run(
        bid_http.container.bids.apply_document_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=retry_job_id,
            files=[
                {
                    "type": "technical",
                    "fileId": "document-gate-output",
                    "content": content,
                }
            ],
            actor_id=bid_http.actor.user_id,
            actor_name=bid_http.actor.name,
        )
    )
    assert len(documents) == 1

    with pytest.raises(DomainError, match="相反的终态结果"):
        asyncio.run(
            bid_http.container.bids.apply_job_failure(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=retry_job_id,
                failed_stage="pending_output",
                message="迟到失败不得覆盖成功",
            )
        )
    assert bid_http.container.store.get_task(task_id, tenant_id="tenant-a").status == "completed"


def test_material_result_cannot_escape_original_job_scope(bid_http: BidHttpHarness) -> None:
    task = bid_http.create_task("材料结果绑定")
    task_id = str(task["id"])
    _set_status(bid_http, task_id, "material_prep")
    selected_id = _create_material(bid_http, task_id, "已选择材料")
    other_id = _create_material(bid_http, task_id, "未选择材料")
    job = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/materials/match",
        headers={"Idempotency-Key": "material-scope"},
        json={"materialIds": [selected_id]},
    )
    assert job.status_code == 202, job.text

    with pytest.raises(DomainError, match="原始任务范围"):
        asyncio.run(
            bid_http.container.bids.apply_material_match_result(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=str(job.json()["data"]["id"]),
                matches=[
                    {
                        "materialId": other_id,
                        "source": "fragment",
                        "sourceId": "fragment-1",
                        "matchConfidence": 0.9,
                    }
                ],
            )
        )
    untouched = bid_http.container.store.get_material(other_id, tenant_id="tenant-a")
    assert untouched.source == "manual"
    assert untouched.match_confidence is None


def test_material_match_result_rejects_material_patched_after_enqueue(bid_http: BidHttpHarness) -> None:
    task = bid_http.create_task("材料匹配快照")
    task_id = str(task["id"])
    _set_status(bid_http, task_id, "material_prep")
    first_id = _create_material(bid_http, task_id, "技术材料")
    changed_id = _create_material(bid_http, task_id, "商务材料")

    job = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/materials/match",
        headers={"Idempotency-Key": "material-snapshot"},
        json={"materialIds": [first_id, changed_id]},
    )
    assert job.status_code == 202, job.text
    job_id = str(job.json()["data"]["id"])
    job_input = bid_http.container.store.get_job_input(
        job_id,
        tenant_id="tenant-a",
        task_id=task_id,
        action=JOB_TYPE_MATERIAL_MATCH,
    )
    assert job_input["materialSnapshots"] == [
        {
            "materialId": first_id,
            "version": 1,
            "source": "manual",
            "sourceId": None,
            "fileId": None,
            "sha256": None,
        },
        {
            "materialId": changed_id,
            "version": 1,
            "source": "manual",
            "sourceId": None,
            "fileId": None,
            "sha256": None,
        },
    ]

    patched = bid_http.client.patch(
        f"/api/v1/bid-tasks/{task_id}/materials/{changed_id}",
        headers={"If-Match": '"1"'},
        json={"sourceId": "user-selected-source"},
    )
    assert patched.status_code == 200, patched.text

    with pytest.raises(DomainError, match="材料已变更"):
        asyncio.run(
            bid_http.container.bids.apply_material_match_result(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=job_id,
                matches=[
                    {
                        "materialId": first_id,
                        "source": "fragment",
                        "sourceId": "fragment-1",
                        "matchConfidence": 0.91,
                    },
                    {
                        "materialId": changed_id,
                        "source": "fragment",
                        "sourceId": "fragment-2",
                        "matchConfidence": 0.92,
                    },
                ],
            )
        )

    first = bid_http.container.store.get_material(first_id, tenant_id="tenant-a")
    changed = bid_http.container.store.get_material(changed_id, tenant_id="tenant-a")
    assert (first.source, first.source_id, first.match_confidence, first.version) == ("manual", None, None, 1)
    assert (changed.source, changed.source_id, changed.match_confidence, changed.version) == (
        "manual",
        "user-selected-source",
        None,
        2,
    )


def test_older_material_match_job_is_rejected_after_newer_empty_result(bid_http: BidHttpHarness) -> None:
    task = bid_http.create_task("材料匹配新旧任务")
    task_id = str(task["id"])
    _set_status(bid_http, task_id, "material_prep")
    material_id = _create_material(bid_http, task_id, "待匹配材料")
    path = f"/api/v1/bid-tasks/{task_id}/materials/match"
    payload = {"materialIds": [material_id]}
    older = bid_http.client.post(path, headers={"Idempotency-Key": "match-older-job"}, json=payload)
    newer = bid_http.client.post(path, headers={"Idempotency-Key": "match-newer-job"}, json=payload)
    assert older.status_code == newer.status_code == 202

    newer_job_id = str(newer.json()["data"]["id"])
    assert (
        asyncio.run(
            bid_http.container.bids.apply_material_match_result(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=newer_job_id,
                matches=[],
            )
        )
        == []
    )
    with pytest.raises(DomainError, match="更新任务取代"):
        asyncio.run(
            bid_http.container.bids.apply_material_match_result(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=str(older.json()["data"]["id"]),
                matches=[
                    {
                        "materialId": material_id,
                        "source": "fragment",
                        "sourceId": "stale-fragment",
                        "matchConfidence": 0.99,
                    }
                ],
            )
        )
    replay = asyncio.run(
        bid_http.container.bids.apply_material_match_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=newer_job_id,
            matches=[
                {
                    "materialId": material_id,
                    "source": "fragment",
                    "sourceId": "must-not-apply",
                    "matchConfidence": 1.0,
                }
            ],
        )
    )
    assert replay == []
    current = bid_http.container.store.get_material(material_id, tenant_id="tenant-a")
    assert (current.source, current.source_id, current.match_confidence, current.version) == ("manual", None, None, 1)


def test_concurrent_idempotency_replay_dispatches_once(bid_http: BidHttpHarness) -> None:
    task = bid_http.create_task("并发幂等任务")
    task_id = str(task["id"])
    original_jobs = bid_http.container.bids.jobs

    class SlowJobs:
        async def enqueue(self, **kwargs: Any):
            await asyncio.sleep(0)
            return await original_jobs.enqueue(**kwargs)

    bid_http.container.bids.jobs = SlowJobs()

    async def enqueue_twice() -> tuple[dict[str, Any], dict[str, Any]]:
        first, second = await asyncio.gather(
            bid_http.container.bids.enqueue_parse(
                bid_http.actor,
                task_id,
                idempotency_key="concurrent-parse",
            ),
            bid_http.container.bids.enqueue_parse(
                bid_http.actor,
                task_id,
                idempotency_key="concurrent-parse",
            ),
        )
        return first, second

    first, second = asyncio.run(enqueue_twice())
    assert first == second
    assert bid_http.container.ports is not None
    assert len(bid_http.container.ports.jobs) == 1


def test_concurrent_parse_with_different_keys_dispatches_once(bid_http: BidHttpHarness) -> None:
    task = bid_http.create_task("并发解析任务")
    task_id = str(task["id"])
    original_files = bid_http.container.bids.files

    class SlowFiles:
        async def assert_accessible(self, **kwargs: Any):
            await asyncio.sleep(0.01)
            return await original_files.assert_accessible(**kwargs)

    bid_http.container.bids.files = SlowFiles()

    async def enqueue_with_different_keys() -> list[dict[str, Any] | BaseException]:
        return await asyncio.gather(
            bid_http.container.bids.enqueue_parse(
                bid_http.actor,
                task_id,
                idempotency_key="concurrent-parse-a",
            ),
            bid_http.container.bids.enqueue_parse(
                bid_http.actor,
                task_id,
                idempotency_key="concurrent-parse-b",
            ),
            return_exceptions=True,
        )

    results = asyncio.run(enqueue_with_different_keys())
    successes = [result for result in results if isinstance(result, dict)]
    failures = [result for result in results if isinstance(result, DomainError)]

    assert len(successes) == len(failures) == 1
    assert failures[0].code == "INVALID_STATE_TRANSITION"
    assert bid_http.container.ports is not None
    assert len(bid_http.container.ports.jobs) == 1


def test_template_result_rejects_material_changed_after_enqueue(bid_http: BidHttpHarness) -> None:
    task = bid_http.create_task("模板快照任务")
    task_id = str(task["id"])
    _set_status(bid_http, task_id, "material_prep")
    material_id = _create_material(bid_http, task_id, "技术模板")

    job = bid_http.container.bids.enqueue_template_generate(
        bid_http.actor,
        task_id,
        {"materialIds": [material_id]},
        idempotency_key="template-snapshot",
    )
    job_ref = asyncio.run(job)
    job_input = bid_http.container.store.get_job_input(
        str(job_ref["id"]),
        tenant_id="tenant-a",
        task_id=task_id,
        action=JOB_TYPE_TEMPLATE_GENERATE,
    )
    assert job_input["materialSnapshots"] == [
        {
            "materialId": material_id,
            "version": 1,
            "fileId": None,
            "sha256": None,
        }
    ]

    bid_http.add_file("user-final-file", file_name="final.pdf", content=b"user-final")
    bid_http.add_file("generated-template", file_name="template.docx", content=b"old-template")
    original_files = bid_http.container.bids.files

    class BindUserFileDuringResultValidation:
        async def assert_accessible(self, **kwargs: Any):
            file_ref = await original_files.assert_accessible(**kwargs)
            if kwargs["file_id"] == "generated-template":
                await bid_http.container.bids.bind_material_file(
                    bid_http.actor,
                    task_id,
                    material_id,
                    {"fileId": "user-final-file"},
                )
            return file_ref

    bid_http.container.bids.files = BindUserFileDuringResultValidation()

    with pytest.raises(DomainError, match="材料已变更"):
        asyncio.run(
            bid_http.container.bids.apply_template_result(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=str(job_ref["id"]),
                bindings=[{"materialId": material_id, "fileId": "generated-template"}],
                actor_id=bid_http.actor.user_id,
            )
        )

    current = bid_http.container.store.get_material(material_id, tenant_id="tenant-a")
    assert current.file_id == "user-final-file"
    assert current.status == "have"


def test_older_template_job_is_rejected_after_newer_partial_result(bid_http: BidHttpHarness) -> None:
    task = bid_http.create_task("模板新旧任务")
    task_id = str(task["id"])
    _set_status(bid_http, task_id, "material_prep")
    first_id = _create_material(bid_http, task_id, "第一份模板")
    second_id = _create_material(bid_http, task_id, "第二份模板")
    path = f"/api/v1/bid-tasks/{task_id}/materials/templates"
    payload = {"materialIds": [first_id, second_id]}
    older = bid_http.client.post(path, headers={"Idempotency-Key": "template-older-job"}, json=payload)
    newer = bid_http.client.post(path, headers={"Idempotency-Key": "template-newer-job"}, json=payload)
    assert older.status_code == newer.status_code == 202
    bid_http.add_file("newer-template-file", file_name="newer.docx", content=b"newer-template")
    bid_http.add_file("older-template-file", file_name="older.docx", content=b"older-template")

    newer_job_id = str(newer.json()["data"]["id"])
    applied = asyncio.run(
        bid_http.container.bids.apply_template_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=newer_job_id,
            bindings=[{"materialId": first_id, "fileId": "newer-template-file"}],
            actor_id=bid_http.actor.user_id,
        )
    )
    assert len(applied) == 1
    with pytest.raises(DomainError, match="更新任务取代"):
        asyncio.run(
            bid_http.container.bids.apply_template_result(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=str(older.json()["data"]["id"]),
                bindings=[{"materialId": second_id, "fileId": "older-template-file"}],
                actor_id=bid_http.actor.user_id,
            )
        )
    replay = asyncio.run(
        bid_http.container.bids.apply_template_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=newer_job_id,
            bindings=[],
            actor_id=bid_http.actor.user_id,
        )
    )
    assert replay == applied
    untouched = bid_http.container.store.get_material(second_id, tenant_id="tenant-a")
    assert untouched.file_id is None
    assert untouched.version == 1


def test_stale_failure_cannot_beat_newer_material_or_template_job(bid_http: BidHttpHarness) -> None:
    for index, action in enumerate(("match", "templates")):
        task = bid_http.create_task(f"旧失败回写-{action}")
        task_id = str(task["id"])
        _set_status(bid_http, task_id, "material_prep")
        material_id = _create_material(bid_http, task_id, f"材料-{index}")
        path = f"/api/v1/bid-tasks/{task_id}/materials/{action}"
        payload = {"materialIds": [material_id]}
        older = bid_http.client.post(
            path,
            headers={"Idempotency-Key": f"stale-failure-old-{index}"},
            json=payload,
        )
        newer = bid_http.client.post(
            path,
            headers={"Idempotency-Key": f"stale-failure-new-{index}"},
            json=payload,
        )
        assert older.status_code == newer.status_code == 202

        with pytest.raises(DomainError, match="更新任务取代"):
            asyncio.run(
                bid_http.container.bids.apply_job_failure(
                    tenant_id="tenant-a",
                    task_id=task_id,
                    job_id=str(older.json()["data"]["id"]),
                    failed_stage="material_prep",
                    message="旧任务迟到失败",
                )
            )

        newer_job_id = str(newer.json()["data"]["id"])
        if action == "match":
            result = asyncio.run(
                bid_http.container.bids.apply_material_match_result(
                    tenant_id="tenant-a",
                    task_id=task_id,
                    job_id=newer_job_id,
                    matches=[],
                )
            )
        else:
            result = asyncio.run(
                bid_http.container.bids.apply_template_result(
                    tenant_id="tenant-a",
                    task_id=task_id,
                    job_id=newer_job_id,
                    bindings=[],
                    actor_id=bid_http.actor.user_id,
                )
            )
        assert result == []
        assert bid_http.container.store.get_task(task_id, tenant_id="tenant-a").status == "material_prep"


def test_latest_document_rollback_job_wins_over_stale_success_and_failure(
    bid_http: BidHttpHarness,
) -> None:
    task = bid_http.create_task("文档回滚最新任务门禁")
    task_id = str(task["id"])
    first_content = make_docx_bytes(sections=["technical"], project_name="回滚源版本一")
    first_version = bid_http.container.bids.documents.append_version(
        tenant_id="tenant-a",
        task_id=task_id,
        doc_type="technical",
        new_id_fn=new_id,
        file_id="rollback-source-one",
        file_name="source-one.docx",
        size_bytes=len(first_content),
        content=first_content,
        created_by_id=bid_http.actor.user_id,
        created_by_name=bid_http.actor.name,
    )
    second_content = make_docx_bytes(sections=["technical"], project_name="回滚源版本二")
    second_version = bid_http.container.bids.documents.append_version(
        tenant_id="tenant-a",
        task_id=task_id,
        doc_type="technical",
        new_id_fn=new_id,
        file_id="rollback-source-two",
        file_name="source-two.docx",
        size_bytes=len(second_content),
        content=second_content,
        created_by_id=bid_http.actor.user_id,
        created_by_name=bid_http.actor.name,
    )
    _set_status(bid_http, task_id, "completed")

    older = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/document-versions/{first_version.id}/rollback",
        headers={"Idempotency-Key": "rollback-latest-older"},
        json={"reason": "恢复源版本一"},
    )
    newer = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/document-versions/{second_version.id}/rollback",
        headers={"Idempotency-Key": "rollback-latest-newer"},
        json={"reason": "恢复源版本二"},
    )
    assert older.status_code == newer.status_code == 202

    newer_job_id = str(newer.json()["data"]["id"])
    applied = asyncio.run(
        bid_http.container.bids.apply_document_rollback_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=newer_job_id,
            target_version_id=second_version.id,
            reason="恢复源版本二",
            actor_id=bid_http.actor.user_id,
            actor_name=bid_http.actor.name,
        )
    )
    assert applied["versionNumber"] == 3
    applied_version = bid_http.container.document_store.get_version(str(applied["id"]), tenant_id="tenant-a")
    assert applied_version.source_version_id == second_version.id

    older_job_id = str(older.json()["data"]["id"])
    with pytest.raises(DomainError, match="更新任务取代"):
        asyncio.run(
            bid_http.container.bids.apply_document_rollback_result(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=older_job_id,
                target_version_id=first_version.id,
                reason="恢复源版本一",
                actor_id=bid_http.actor.user_id,
                actor_name=bid_http.actor.name,
            )
        )
    with pytest.raises(DomainError, match="更新任务取代"):
        asyncio.run(
            bid_http.container.bids.apply_job_failure(
                tenant_id="tenant-a",
                task_id=task_id,
                job_id=older_job_id,
                failed_stage="pending_output",
                message="旧回滚任务迟到失败",
            )
        )

    replay = asyncio.run(
        bid_http.container.bids.apply_document_rollback_result(
            tenant_id="tenant-a",
            task_id=task_id,
            job_id=newer_job_id,
            target_version_id=first_version.id,
            reason="缓存重放不得再次回滚",
            actor_id="different-actor",
            actor_name="different-actor",
        )
    )
    assert replay == applied
    versions = bid_http.container.document_store.list_versions_by_task(
        tenant_id="tenant-a",
        task_id=task_id,
    )
    assert len(versions) == 3
    assert max(versions, key=lambda item: item.version_number).id == applied["id"]
    assert bid_http.container.store.get_task(task_id, tenant_id="tenant-a").status == "completed"
