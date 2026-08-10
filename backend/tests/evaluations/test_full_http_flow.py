"""M6 的完整 HTTP 主流程，确保所有公开路由可由同一状态链实际调用."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domains.evaluations.container import build_m6_container
from app.domains.evaluations.ports import (
    AuthPrincipal,
    BidMaterialSnapshot,
    BidTaskSnapshot,
    FileRefSnapshot,
)
from app.domains.evaluations.router import get_actor
from app.domains.evaluations.router import router as evaluations_router
from app.domains.portal.router import router as portal_router


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _app() -> tuple[TestClient, object, AuthPrincipal]:
    container = build_m6_container()
    actor = AuthPrincipal(user_id="u-owner", tenant_id="t-1", name="负责人", role="admin")
    app = FastAPI()
    app.state.m6 = container
    app.include_router(evaluations_router, prefix="/api/v1")
    app.include_router(portal_router, prefix="/api/v1")
    app.dependency_overrides[get_actor] = lambda: actor
    return TestClient(app), container, actor


def _data(response, expected_status: int = 200):
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["success"] is True
    assert body["requestId"]
    return body["data"]


def test_complete_internal_and_supplier_http_flow() -> None:
    client, container, actor = _app()
    assert container.ports is not None
    now = datetime.now(UTC)

    bid_id = "bid-source-1"
    container.ports.bid_snapshots[f"t-1:{bid_id}"] = BidTaskSnapshot(
        id=bid_id,
        tenant_id="t-1",
        project_name="来源项目",
        tender_no="ZB-SOURCE",
        tender_entity="建设单位",
        deadline=now + timedelta(days=5),
        budget_amount=Decimal("100000.00"),
        materials=(
            BidMaterialSnapshot(
                name="来源资质",
                category="qualification",
                required=True,
                allowed_mime_types=("application/pdf",),
                max_size_bytes=5_000_000,
                sort_order=0,
            ),
        ),
    )
    imported = _data(
        client.post(f"/api/v1/evaluations/from-bid-task/{bid_id}", json={"copyMaterials": True}),
        201,
    )
    assert imported["sourceBidTaskId"] == bid_id

    created = _data(
        client.post(
            "/api/v1/evaluations",
            json={
                "projectName": "HTTP 全流程评标",
                "tenderNo": "ZB-HTTP-001",
                "tenderEntity": "建设单位",
                "budgetAmount": "5000000.00",
                "currency": "CNY",
                "assigneeId": actor.user_id,
                "supplierDeadline": _iso(now + timedelta(days=3)),
                "evaluationStartAt": _iso(now + timedelta(days=4)),
                "evaluationEndAt": _iso(now + timedelta(days=10)),
            },
        ),
        201,
    )
    evaluation_id = created["id"]

    updated = _data(
        client.patch(
            f"/api/v1/evaluations/{evaluation_id}",
            headers={"If-Match": str(created["version"])},
            json={"description": "已更新说明"},
        )
    )
    assert updated["version"] == created["version"] + 1
    stale = client.patch(
        f"/api/v1/evaluations/{evaluation_id}",
        headers={"If-Match": str(created["version"])},
        json={"description": "过期更新"},
    )
    assert stale.status_code == 409

    materials = _data(
        client.put(
            f"/api/v1/evaluations/{evaluation_id}/materials",
            json={
                "items": [
                    {
                        "name": "营业执照",
                        "category": "qualification",
                        "required": True,
                        "allowedMimeTypes": ["application/pdf"],
                        "maxSizeBytes": 10_000_000,
                        "sortOrder": 0,
                    }
                ]
            },
        )
    )
    criteria = _data(
        client.put(
            f"/api/v1/evaluations/{evaluation_id}/criteria",
            json={
                "items": [
                    {
                        "name": "技术方案",
                        "category": "technical",
                        "maxScore": "100.00",
                        "weightPercent": "60.00",
                        "method": "expert",
                        "description": "技术完整性",
                        "sortOrder": 0,
                    },
                    {
                        "name": "商务报价",
                        "category": "commercial",
                        "maxScore": "100.00",
                        "weightPercent": "40.00",
                        "method": "formula",
                        "formula": "min/quote*100",
                        "description": "价格分",
                        "sortOrder": 1,
                    },
                ]
            },
        )
    )
    _data(
        client.put(
            f"/api/v1/evaluations/{evaluation_id}/review-settings",
            json={
                "multiRoundPricing": True,
                "maxRounds": 2,
                "supplementDeadlineMinutes": 1440,
                "allowModifyBeforeDeadline": True,
                "notifyOnMissing": True,
                "closeSubmissionAtDeadline": True,
            },
        )
    )
    _data(
        client.put(
            f"/api/v1/evaluations/{evaluation_id}/reviewers",
            json={"reviewerIds": ["u-reviewer-1"]},
        )
    )
    suppliers = _data(
        client.put(
            f"/api/v1/evaluations/{evaluation_id}/suppliers",
            json={
                "items": [
                    {
                        "name": "甲供应商",
                        "contactName": "张三",
                        "email": "supplier-a@example.test",
                        "phone": "13800000000",
                    },
                    {
                        "name": "乙供应商",
                        "contactName": "李四",
                        "email": "supplier-b@example.test",
                    },
                ]
            },
        )
    )

    assert _data(client.get("/api/v1/evaluations/stats"))["total"] >= 2
    assert _data(client.get("/api/v1/evaluations", params={"keyword": "HTTP"}))[0]["id"] == evaluation_id
    detail = _data(client.get(f"/api/v1/evaluations/{evaluation_id}"))
    assert detail["id"] == evaluation_id
    assert detail["description"] == "已更新说明"
    audit_response = client.get(
        f"/api/v1/evaluations/{evaluation_id}/audit-events",
        params={"action": "evaluation.created", "page": 1, "pageSize": 10},
    )
    audit_events = _data(audit_response)
    assert audit_response.json()["meta"]["total"] == 1
    assert audit_events[0]["aggregateId"] == evaluation_id
    assert audit_events[0]["action"] == "evaluation.created"
    assert _data(client.post(f"/api/v1/evaluations/{evaluation_id}/validate"))["valid"] is True
    assert _data(client.get(f"/api/v1/evaluations/{evaluation_id}/preview"))["validation"]["valid"] is True

    published = _data(
        client.post(
            f"/api/v1/evaluations/{evaluation_id}/publish",
            headers={"Idempotency-Key": "publish-http"},
        )
    )
    invite_code = published["invites"][0]["inviteUrl"].rsplit("/", 1)[-1]
    assert len(_data(client.get(f"/api/v1/evaluations/{evaluation_id}/suppliers"))) == 2
    assert len(_data(client.get(f"/api/v1/evaluations/{evaluation_id}/supplier-invites"))) == 2
    rotated = _data(
        client.post(
            f"/api/v1/evaluations/{evaluation_id}/supplier-invites/{suppliers[1]['id']}/rotate",
            json={"reason": "重新发送"},
        )
    )
    assert rotated["status"] == "active"
    assert _data(
        client.post(
            f"/api/v1/evaluations/{evaluation_id}/supplier-invites/{suppliers[1]['id']}/revoke",
            json={"reason": "联系人变更"},
        )
    ) == {"revoked": True}

    session = _data(client.post("/api/v1/portal/session/exchange", json={"inviteCode": invite_code}))
    token = session["portalAccessToken"]
    portal_headers = {"Authorization": f"Bearer {token}"}
    refreshed = _data(client.post("/api/v1/portal/session/refresh"))
    token = refreshed["portalAccessToken"]
    portal_headers = {"Authorization": f"Bearer {token}"}
    assert _data(client.get("/api/v1/portal/me", headers=portal_headers))["supplier"]["id"] == suppliers[0]["id"]
    assert len(_data(client.get("/api/v1/portal/materials", headers=portal_headers))) == 1

    file_id = "file-supplier-a"
    container.ports.files[file_id] = FileRefSnapshot(
        id=file_id,
        file_name="license.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="a" * 64,
        scan_status="clean",
        created_at=now,
    )
    material_path = f"/api/v1/portal/materials/{materials[0]['id']}/file"
    _data(client.put(material_path, headers=portal_headers, json={"fileId": file_id}))
    _data(client.delete(material_path, headers=portal_headers))
    _data(client.put(material_path, headers=portal_headers, json={"fileId": file_id}))
    assert (
        _data(
            client.put(
                "/api/v1/portal/draft",
                headers=portal_headers,
                json={"note": "资料已核对", "quoteDraft": "4800000.00"},
            )
        )["version"]
        == 1
    )
    receipt = _data(
        client.post(
            "/api/v1/portal/submit",
            headers={**portal_headers, "Idempotency-Key": "submit-http"},
            json={"confirmed": True},
        )
    )
    assert receipt["submittedMaterialCount"] == 1
    binary_receipt = client.get("/api/v1/portal/receipt", headers=portal_headers)
    assert binary_receipt.status_code == 200
    assert binary_receipt.content.startswith(b"%PDF")
    assert _data(client.get("/api/v1/portal/activity", headers=portal_headers))
    submissions = _data(client.get(f"/api/v1/evaluations/{evaluation_id}/suppliers/{suppliers[0]['id']}/submissions"))
    assert submissions[0]["file"]["id"] == file_id

    notice = _data(
        client.post(
            f"/api/v1/evaluations/{evaluation_id}/supplement-notices",
            json={
                "supplierId": suppliers[0]["id"],
                "materialIds": [materials[0]["id"]],
                "message": "请补充盖章页",
                "deadlineMinutes": 60,
            },
        ),
        201,
    )
    assert len(_data(client.get(f"/api/v1/evaluations/{evaluation_id}/supplement-notices"))) == 1
    assert len(_data(client.get("/api/v1/portal/notices", headers=portal_headers))) == 1
    responded = _data(
        client.post(
            f"/api/v1/portal/notices/{notice['id']}/respond",
            headers=portal_headers,
            json={"fileBindings": [{"materialId": materials[0]["id"], "fileId": file_id}]},
        )
    )
    assert responded["status"] == "responded"

    price_round = _data(
        client.post(
            f"/api/v1/evaluations/{evaluation_id}/price-rounds",
            json={
                "title": "第一轮报价",
                "opensAt": _iso(now - timedelta(minutes=1)),
                "deadline": _iso(now + timedelta(hours=2)),
                "eligibleSupplierIds": [suppliers[0]["id"]],
                "rankingVisibleToSupplier": True,
            },
        ),
        201,
    )
    assert len(_data(client.get(f"/api/v1/evaluations/{evaluation_id}/price-rounds"))) == 1
    assert len(_data(client.get("/api/v1/portal/price-rounds", headers=portal_headers))) == 1
    quote = _data(
        client.post(
            f"/api/v1/portal/price-rounds/{price_round['id']}/quotes",
            headers={**portal_headers, "Idempotency-Key": "quote-http"},
            json={"amount": "4700000.00", "currency": "CNY"},
        )
    )
    assert quote["amount"] == "4700000.00"
    assert _data(client.get(f"/api/v1/evaluations/{evaluation_id}/price-comparison"))["rounds"]
    assert (
        _data(client.post(f"/api/v1/evaluations/{evaluation_id}/price-rounds/{price_round['id']}/close"))["status"]
        == "closed"
    )

    assert _data(client.post(f"/api/v1/evaluations/{evaluation_id}/material-checks"), 202)["status"] == "queued"
    assert _data(client.get(f"/api/v1/evaluations/{evaluation_id}/material-checks/latest"))["status"] == "queued"
    assert _data(client.post(f"/api/v1/evaluations/{evaluation_id}/risk-checks"), 202)["status"] == "queued"
    risks = _data(client.get(f"/api/v1/evaluations/{evaluation_id}/risks", params={"decision": "pending"}))
    decided = _data(
        client.post(
            f"/api/v1/evaluations/{evaluation_id}/risks/{risks[0]['id']}/decision",
            json={"decision": "passed", "reason": "人工核验通过"},
        )
    )
    assert decided["decision"] == "passed"

    asyncio.run(container.scoring.advance_to_pending(actor, evaluation_id))
    assert _data(client.post(f"/api/v1/evaluations/{evaluation_id}/ai-scoring"), 202)["status"] == "queued"
    scores = _data(client.get(f"/api/v1/evaluations/{evaluation_id}/scores", params={"category": "technical"}))
    score = scores[0]
    adjusted = _data(
        client.patch(
            f"/api/v1/evaluations/{evaluation_id}/scores/{score['supplierId']}/{criteria[0]['id']}",
            headers={"If-Match": str(score["version"])},
            json={"humanScore": "88.00", "adjustmentReason": "方案完整"},
        )
    )
    assert adjusted["humanScore"] == "88.00"
    assert _data(
        client.post(
            f"/api/v1/evaluations/{evaluation_id}/scores/confirm",
            json={"comment": "评分确认"},
        )
    ) == {"confirmed": True}
    assert _data(client.get(f"/api/v1/evaluations/{evaluation_id}/ranking"))["rows"]

    assert (
        _data(
            client.post(
                f"/api/v1/evaluations/{evaluation_id}/reports",
                json={"formats": ["pdf", "docx"]},
            ),
            202,
        )["status"]
        == "queued"
    )
    report_file_id = "report-file-pdf"
    container.ports.files[report_file_id] = FileRefSnapshot(
        id=report_file_id,
        file_name="report.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        sha256="b" * 64,
        scan_status="clean",
        created_at=now,
    )
    report = asyncio.run(
        container.scoring.apply_job_result_report(
            tenant_id="t-1",
            evaluation_id=evaluation_id,
            format="pdf",
            file_id=report_file_id,
            actor_id=actor.user_id,
            actor_name=actor.name,
        )
    )
    assert len(_data(client.get(f"/api/v1/evaluations/{evaluation_id}/reports"))) == 1
    report_download = client.get(f"/api/v1/evaluations/{evaluation_id}/reports/{report.id}/download")
    assert report_download.status_code == 200
    assert report_download.content.startswith(b"%PDF")

    closed = _data(
        client.post(
            f"/api/v1/evaluations/{evaluation_id}/close",
            headers={"Idempotency-Key": "close-http"},
            json={"resultSummary": "评标完成"},
        )
    )
    assert closed["status"] == "closed"

    cancelled = _data(
        client.post(
            f"/api/v1/evaluations/{imported['id']}/cancel",
            json={"reason": "取消导入测试"},
        )
    )
    assert cancelled["status"] == "cancelled"
    assert _data(client.post("/api/v1/portal/session/logout", headers=portal_headers)) == {"loggedOut": True}
