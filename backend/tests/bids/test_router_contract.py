"""M5 bid-task HTTP contract, authorization, concurrency and idempotency tests."""

from __future__ import annotations

import asyncio
import io
import zipfile
from hashlib import sha256

import pytest

from app.contracts.generated.models import (
    BatchBindResult,
    BidBoardColumn,
    BidMaterial,
    BidTask,
    BidTaskDetail,
    BidTaskStats,
    JobRef,
    TaskAssignment,
    TenderRequirements,
)
from app.domains.bids.errors import DomainError
from app.domains.bids.ports import AuthPrincipal
from app.domains.bids.router import auth_principal_from_context
from app.domains.bids.router import router as bids_router

from .conftest import BidHttpHarness

EXPECTED_BID_OPERATIONS = {
    ("GET", "/bid-tasks/stats"),
    ("GET", "/bid-tasks"),
    ("POST", "/bid-tasks"),
    ("GET", "/bid-tasks/board"),
    ("GET", "/bid-tasks/{taskId}"),
    ("PATCH", "/bid-tasks/{taskId}"),
    ("POST", "/bid-tasks/{taskId}/clone"),
    ("POST", "/bid-tasks/{taskId}/archive"),
    ("POST", "/bid-tasks/{taskId}/assignments"),
    ("DELETE", "/bid-tasks/{taskId}/assignments/{userId}"),
    ("PUT", "/bid-tasks/{taskId}/tender-file"),
    ("POST", "/bid-tasks/{taskId}/parse"),
    ("GET", "/bid-tasks/{taskId}/requirements"),
    ("PATCH", "/bid-tasks/{taskId}/requirements"),
    ("GET", "/bid-tasks/{taskId}/materials"),
    ("POST", "/bid-tasks/{taskId}/materials"),
    ("PATCH", "/bid-tasks/{taskId}/materials/{materialId}"),
    ("DELETE", "/bid-tasks/{taskId}/materials/{materialId}"),
    ("POST", "/bid-tasks/{taskId}/materials/match"),
    ("PUT", "/bid-tasks/{taskId}/materials/{materialId}/file"),
    ("DELETE", "/bid-tasks/{taskId}/materials/{materialId}/file"),
    ("POST", "/bid-tasks/{taskId}/materials/batch-bind"),
    ("GET", "/bid-tasks/{taskId}/materials/export"),
    ("POST", "/bid-tasks/{taskId}/materials/templates"),
    ("POST", "/bid-tasks/{taskId}/reviews"),
    ("GET", "/bid-tasks/{taskId}/reviews/latest"),
    ("POST", "/bid-tasks/{taskId}/review-findings/{findingId}/decision"),
    ("POST", "/bid-tasks/{taskId}/documents"),
    ("GET", "/bid-tasks/{taskId}/documents"),
    ("GET", "/bid-tasks/{taskId}/documents/{documentId}/download"),
    ("GET", "/bid-tasks/{taskId}/document-versions"),
    ("GET", "/bid-tasks/{taskId}/document-versions/compare"),
    ("POST", "/bid-tasks/{taskId}/document-versions/{versionId}/rollback"),
}


def test_router_exposes_all_33_bid_operations() -> None:
    actual = {
        (method, route.path)
        for route in bids_router.routes
        if getattr(route, "path", "").startswith("/bid-tasks")
        for method in route.methods
    }
    assert actual == EXPECTED_BID_OPERATIONS


def test_aggregate_router_shares_one_actor_dependency_across_m5_domains(bid_http: BidHttpHarness) -> None:
    assert bid_http.client.get("/api/v1/qualifications/stats").status_code == 200
    assert bid_http.client.get("/api/v1/fragments/stats").status_code == 200


def test_actor_context_rejects_unknown_global_role() -> None:
    with pytest.raises(DomainError) as captured:
        auth_principal_from_context({"id": "external-user", "tenant_id": "tenant-a", "role": "supplier"})
    assert captured.value.code == "FORBIDDEN"


def test_create_list_detail_and_material_normal_path(bid_http: BidHttpHarness) -> None:
    created = bid_http.create_task()
    BidTask.model_validate(created)
    task_id = str(created["id"])

    listing = bid_http.client.get("/api/v1/bid-tasks", headers={"X-Request-Id": "request-m5-list"})
    assert listing.status_code == 200
    assert listing.headers["X-Request-Id"] == "request-m5-list"
    assert listing.json()["data"][0]["id"] == task_id

    detail = bid_http.client.get(f"/api/v1/bid-tasks/{task_id}")
    assert detail.status_code == 200
    detail_data = detail.json()["data"]
    BidTaskDetail.model_validate(detail_data)
    tender_file = detail_data["tenderFile"]
    assert len(tender_file["sha256"]) == 64
    assert tender_file["scanStatus"] == "clean"
    assert tender_file["createdAt"].endswith("Z")

    assignment = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/assignments",
        json={"userId": "user-collaborator", "roleInTask": "collaborator"},
    )
    assert assignment.status_code == 200
    TaskAssignment.model_validate(assignment.json()["data"])

    material = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/materials",
        json={
            "name": "营业执照",
            "category": "qualification",
            "requirement": "有效期内",
            "required": True,
            "sortOrder": 0,
        },
    )
    assert material.status_code == 200, material.text
    material_data = material.json()["data"]
    BidMaterial.model_validate(material_data)
    bid_http.add_file("material-file", file_name="material.pdf")
    batch = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/materials/batch-bind",
        json={
            "bindings": [{"materialId": material_data["id"], "fileId": "material-file"}],
            "replaceExisting": False,
        },
    )
    assert batch.status_code == 200, batch.text
    BatchBindResult.model_validate(batch.json()["data"])
    materials = bid_http.client.get(f"/api/v1/bid-tasks/{task_id}/materials")
    assert materials.status_code == 200
    assert materials.json()["data"][0]["name"] == "营业执照"

    exported = bid_http.client.get(f"/api/v1/bid-tasks/{task_id}/materials/export")
    assert exported.status_code == 200
    assert exported.headers["X-File-Sha256"] == sha256(exported.content).hexdigest()
    with zipfile.ZipFile(io.BytesIO(exported.content)) as workbook:
        assert "xl/worksheets/sheet1.xml" in workbook.namelist()

    BidTaskStats.model_validate(bid_http.client.get("/api/v1/bid-tasks/stats").json()["data"])
    for column in bid_http.client.get("/api/v1/bid-tasks/board").json()["data"]:
        BidBoardColumn.model_validate(column)


def test_patch_endpoints_require_strict_if_match_and_reject_stale_versions(
    bid_http: BidHttpHarness,
) -> None:
    task = bid_http.create_task()
    task_id = str(task["id"])

    missing = bid_http.client.patch(f"/api/v1/bid-tasks/{task_id}", json={"projectName": "缺少版本"})
    assert missing.status_code == 422
    unquoted = bid_http.client.patch(
        f"/api/v1/bid-tasks/{task_id}",
        headers={"If-Match": "1"},
        json={"projectName": "错误格式"},
    )
    assert unquoted.status_code == 422

    updated = bid_http.client.patch(
        f"/api/v1/bid-tasks/{task_id}",
        headers={"If-Match": '"1"'},
        json={"projectName": "已更新项目"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["projectName"] == "已更新项目"
    assert updated.json()["data"]["version"] == 2

    stale = bid_http.client.patch(
        f"/api/v1/bid-tasks/{task_id}",
        headers={"If-Match": '"1"'},
        json={"projectName": "过期更新"},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "VERSION_CONFLICT"

    requirements = bid_http.client.patch(
        f"/api/v1/bid-tasks/{task_id}/requirements",
        headers={"If-Match": '"1"'},
        json={"projectInfo": {"budgetAmount": "100.00"}},
    )
    assert requirements.status_code == 200, requirements.text
    assert requirements.json()["data"]["version"] == 2
    TenderRequirements.model_validate(requirements.json()["data"])

    material = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/materials",
        json={
            "name": "技术方案",
            "category": "technical",
            "requirement": "完整",
            "required": True,
            "sortOrder": 1,
        },
    ).json()["data"]
    material_update = bid_http.client.patch(
        f"/api/v1/bid-tasks/{task_id}/materials/{material['id']}",
        headers={"If-Match": '"1"'},
        json={"sortOrder": 2},
    )
    assert material_update.status_code == 200, material_update.text
    assert material_update.json()["data"]["sortOrder"] == 2


def test_cross_tenant_and_unassigned_access_are_hidden_or_forbidden(bid_http: BidHttpHarness) -> None:
    task = bid_http.create_task()
    task_id = str(task["id"])

    bid_http.actor = AuthPrincipal(
        user_id="other-admin",
        tenant_id="tenant-b",
        name="其他租户管理员",
        role="admin",
    )
    cross_tenant = bid_http.client.get(f"/api/v1/bid-tasks/{task_id}")
    assert cross_tenant.status_code == 404

    bid_http.actor = AuthPrincipal(
        user_id="unassigned-member",
        tenant_id="tenant-a",
        name="未分配成员",
        role="member",
    )
    unassigned = bid_http.client.get(f"/api/v1/bid-tasks/{task_id}")
    assert unassigned.status_code == 403


def test_global_roles_cannot_gain_extra_rights_from_task_relationships(
    bid_http: BidHttpHarness,
) -> None:
    task = bid_http.create_task("RBAC boundary task")
    task_id = str(task["id"])
    assigned = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/assignments",
        json={"userId": "user-reviewer", "roleInTask": "reviewer"},
    )
    assert assigned.status_code == 200, assigned.text

    bid_http.actor = AuthPrincipal(
        user_id="user-reviewer",
        tenant_id="tenant-a",
        name="Reviewer",
        role="reviewer",
    )
    assert bid_http.client.get(f"/api/v1/bid-tasks/{task_id}").status_code == 200
    forbidden_edit = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/materials",
        json={
            "name": "Forbidden reviewer edit",
            "category": "technical",
            "requirement": "Must stay read-only",
            "required": True,
            "sortOrder": 0,
        },
    )
    assert forbidden_edit.status_code == 403

    bid_http.actor = AuthPrincipal(
        user_id="user-owner",
        tenant_id="tenant-a",
        name="Supplier with matching assignee id",
        role="supplier",
    )
    assert bid_http.client.get(f"/api/v1/bid-tasks/{task_id}").status_code == 403


def test_parse_idempotency_requires_key_and_is_scoped_by_task(bid_http: BidHttpHarness) -> None:
    first_task = bid_http.create_task("幂等任务一")
    first_path = f"/api/v1/bid-tasks/{first_task['id']}/parse"
    missing = bid_http.client.post(first_path)
    assert missing.status_code == 422

    headers = {"Idempotency-Key": "same-parse-key"}
    first = bid_http.client.post(first_path, headers=headers)
    repeated = bid_http.client.post(first_path, headers=headers)
    assert first.status_code == repeated.status_code == 202
    assert first.json()["data"] == repeated.json()["data"]
    assert bid_http.container.ports is not None
    assert len(bid_http.container.ports.jobs) == 1

    second_task = bid_http.create_task("幂等任务二")
    second = bid_http.client.post(
        f"/api/v1/bid-tasks/{second_task['id']}/parse",
        headers=headers,
    )
    assert second.status_code == 202
    assert second.json()["data"]["id"] != first.json()["data"]["id"]
    assert len(bid_http.container.ports.jobs) == 2


def test_idempotent_replay_does_not_bypass_authorization_or_tenant_isolation(
    bid_http: BidHttpHarness,
) -> None:
    task = bid_http.create_task("权限幂等任务")
    path = f"/api/v1/bid-tasks/{task['id']}/parse"
    headers = {"Idempotency-Key": "authorization-key"}
    assert bid_http.client.post(path, headers=headers).status_code == 202

    bid_http.actor = AuthPrincipal(
        user_id="unassigned-member",
        tenant_id="tenant-a",
        name="未分配成员",
        role="member",
    )
    assert bid_http.client.post(path, headers=headers).status_code == 403

    bid_http.actor = AuthPrincipal(
        user_id="other-admin",
        tenant_id="tenant-b",
        name="其他租户管理员",
        role="admin",
    )
    assert bid_http.client.post(path, headers=headers).status_code == 404


def test_every_bid_async_action_replays_the_same_job_for_the_same_key(bid_http: BidHttpHarness) -> None:
    task = bid_http.create_task("异步动作幂等任务")
    task_id = str(task["id"])
    stored = bid_http.container.store.get_task(task_id, tenant_id="tenant-a")
    stored.status = "material_prep"
    stored.current_step = 3
    stored.progress_percent = 35
    bid_http.container.store.save_task(stored)

    material = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/materials",
        json={
            "name": "技术方案",
            "category": "technical",
            "requirement": "完整响应",
            "required": True,
            "sortOrder": 0,
        },
    ).json()["data"]
    material_id = str(material["id"])

    actions = [
        (
            f"/api/v1/bid-tasks/{task_id}/materials/match",
            "material-match-key",
            {"materialIds": [material_id]},
        ),
        (
            f"/api/v1/bid-tasks/{task_id}/materials/templates",
            "material-template-key",
            {"materialIds": [material_id]},
        ),
        (
            f"/api/v1/bid-tasks/{task_id}/reviews",
            "review-idempotency-key",
            {"types": ["content"]},
        ),
        (
            f"/api/v1/bid-tasks/{task_id}/documents",
            "document-idempotency-key",
            {
                "mode": "split",
                "sections": ["technical"],
                "templateMode": "standard",
                "includeWatermark": False,
            },
        ),
    ]

    for path, key, payload in actions:
        missing_key = bid_http.client.post(path, json=payload)
        assert missing_key.status_code == 422
        headers = {"Idempotency-Key": key}
        first = bid_http.client.post(path, headers=headers, json=payload)
        repeated = bid_http.client.post(path, headers=headers, json=payload)
        assert first.status_code == repeated.status_code == 202
        assert first.json()["data"] == repeated.json()["data"]
        JobRef.model_validate(first.json()["data"])
        if path.endswith("/reviews"):
            asyncio.run(
                bid_http.container.bids.apply_review_result(
                    tenant_id="tenant-a",
                    task_id=task_id,
                    job_id=str(first.json()["data"]["id"]),
                    summary="审核通过",
                    findings=[],
                )
            )

    assert bid_http.container.ports is not None
    assert len(bid_http.container.ports.jobs) == 4


def test_request_validation_rejects_explicit_null_and_missing_material_category(
    bid_http: BidHttpHarness,
) -> None:
    task = bid_http.create_task("严格请求校验")
    task_id = str(task["id"])

    null_update = bid_http.client.patch(
        f"/api/v1/bid-tasks/{task_id}",
        headers={"If-Match": '"1"'},
        json={"projectName": None},
    )
    assert null_update.status_code == 422

    missing_category = bid_http.client.post(
        f"/api/v1/bid-tasks/{task_id}/materials",
        json={
            "name": "无分类材料",
            "requirement": "不得触发服务端 KeyError",
            "required": True,
            "sortOrder": 0,
        },
    )
    assert missing_category.status_code == 422
