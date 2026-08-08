"""评标主流程服务测试。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.domains.evaluations.container import build_m6_container
from app.domains.evaluations.errors import DomainError
from app.domains.evaluations.ids import new_id
from app.domains.evaluations.ports import AuthPrincipal, BidMaterialSnapshot, BidTaskSnapshot, FileRefSnapshot


def _actor(role: str = "admin") -> AuthPrincipal:
    return AuthPrincipal(user_id="u-owner", tenant_id="t-1", name="负责人", role=role)  # type: ignore[arg-type]


def _dates() -> dict[str, str]:
    now = datetime.now(UTC)
    return {
        "supplierDeadline": (now + timedelta(days=3)).isoformat().replace("+00:00", "Z"),
        "evaluationStartAt": (now + timedelta(days=4)).isoformat().replace("+00:00", "Z"),
        "evaluationEndAt": (now + timedelta(days=10)).isoformat().replace("+00:00", "Z"),
    }


async def _configured_evaluation(container, actor: AuthPrincipal):
    dates = _dates()
    created = await container.evaluations.create_draft(
        actor,
        {
            "projectName": "智慧园区弱电工程",
            "tenderNo": "ZB-2026-001",
            "tenderEntity": "某市城投",
            "budgetAmount": "5000000.00",
            "currency": "CNY",
            "assigneeId": actor.user_id,
            **dates,
        },
    )
    eid = created["id"]
    materials = await container.evaluations.put_materials(
        actor,
        eid,
        [
            {
                "name": "营业执照",
                "category": "qualification",
                "required": True,
                "allowedMimeTypes": ["application/pdf"],
                "maxSizeBytes": 10_000_000,
                "sortOrder": 0,
            }
        ],
    )
    criteria = await container.evaluations.put_criteria(
        actor,
        eid,
        [
            {
                "name": "技术方案",
                "category": "technical",
                "maxScore": "100.00",
                "weightPercent": "60.00",
                "method": "expert",
                "description": "技术方案完整性",
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
        ],
    )
    await container.evaluations.put_review_settings(
        actor,
        eid,
        {
            "multiRoundPricing": True,
            "maxRounds": 2,
            "supplementDeadlineMinutes": 1440,
            "allowModifyBeforeDeadline": True,
            "notifyOnMissing": True,
            "closeSubmissionAtDeadline": True,
        },
    )
    await container.evaluations.put_reviewers(actor, eid, ["u-reviewer-1"])
    suppliers = await container.evaluations.put_suppliers(
        actor,
        eid,
        [
            {
                "name": "甲供应商",
                "contactName": "张三",
                "email": "a@example.com",
                "phone": "13800000000",
            },
            {
                "name": "乙供应商",
                "contactName": "李四",
                "email": "b@example.com",
            },
        ],
    )
    return eid, materials, criteria, suppliers


@pytest.mark.asyncio
async def test_create_validate_publish_idempotent() -> None:
    container = build_m6_container()
    actor = _actor()
    eid, _, _, suppliers = await _configured_evaluation(container, actor)
    validation = await container.evaluations.validate(actor, eid)
    assert validation["valid"] is True
    first = await container.evaluations.publish(actor, eid, idempotency_key="pub-1")
    second = await container.evaluations.publish(actor, eid, idempotency_key="pub-1")
    assert first["evaluation"]["status"] == "collecting"
    assert first == second
    assert len(first["invites"]) == 2
    assert "****" in first["invites"][0]["inviteCodeMasked"]
    assert suppliers[0]["email"] == "a@example.com"


@pytest.mark.asyncio
async def test_from_bid_snapshot_port_only() -> None:
    container = build_m6_container()
    assert container.ports is not None
    bid_id = new_id()
    container.ports.bid_snapshots[f"t-1:{bid_id}"] = BidTaskSnapshot(
        id=bid_id,
        tenant_id="t-1",
        project_name="导入项目",
        tender_no="ZB-IMP",
        tender_entity="业主",
        deadline=datetime.now(UTC) + timedelta(days=5),
        budget_amount=Decimal("100000.00"),
        materials=(
            BidMaterialSnapshot(
                name="资质证明",
                category="qualification",
                required=True,
                allowed_mime_types=("application/pdf",),
                max_size_bytes=5_000_000,
                sort_order=0,
            ),
        ),
    )
    detail = await container.evaluations.create_from_bid_task(_actor(), bid_id, copy_materials=True)
    assert detail["sourceBidTaskId"] == bid_id
    assert len(detail["materials"]) == 1


@pytest.mark.asyncio
async def test_missing_bid_snapshot_maps_to_domain_not_found() -> None:
    container = build_m6_container()
    with pytest.raises(DomainError) as exc:
        await container.evaluations.create_from_bid_task(_actor(), "missing-bid")
    assert exc.value.code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_cross_tenant_not_found() -> None:
    container = build_m6_container()
    actor = _actor()
    eid, _, _, _ = await _configured_evaluation(container, actor)
    other = AuthPrincipal(user_id="u2", tenant_id="t-other", name="其他", role="admin")
    with pytest.raises(DomainError) as exc:
        await container.evaluations.get_detail(other, eid)
    assert exc.value.code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_portal_isolation_and_submit_idempotent() -> None:
    container = build_m6_container()
    assert container.ports is not None
    actor = _actor()
    eid, materials, _, _ = await _configured_evaluation(container, actor)
    published = await container.evaluations.publish(actor, eid, idempotency_key="pub-2")
    invite_a = published["invites"][0]["inviteUrl"].rsplit("/", 1)[-1]
    invite_b = published["invites"][1]["inviteUrl"].rsplit("/", 1)[-1]

    session_a = await container.portal.exchange(invite_a)
    with pytest.raises(DomainError):
        await container.portal.exchange(invite_a)  # 重放

    session_b = await container.portal.exchange(invite_b)
    principal_a = container.portal.resolve_principal(session_a["portalAccessToken"])
    principal_b = container.portal.resolve_principal(session_b["portalAccessToken"])
    assert principal_a.supplier_id != principal_b.supplier_id

    file_id = new_id()
    container.ports.files[file_id] = FileRefSnapshot(
        id=file_id,
        file_name="license.pdf",
        mime_type="application/pdf",
        size_bytes=1000,
        sha256="a" * 64,
        scan_status="clean",
        created_at=datetime.now(UTC),
    )
    await container.portal.put_material_file(principal_a, materials[0]["id"], file_id)
    receipt1 = await container.portal.submit(principal_a, confirmed=True, idempotency_key="sub-1")
    receipt2 = await container.portal.submit(principal_a, confirmed=True, idempotency_key="sub-1")
    assert receipt1 == receipt2
    assert receipt1["submittedMaterialCount"] == 1

    # B 不能看到 A 的提交
    subs_b = container.store.list_submissions(evaluation_id=eid, supplier_id=principal_b.supplier_id)
    assert subs_b == []


@pytest.mark.asyncio
async def test_score_adjust_requires_reason_and_audit() -> None:
    container = build_m6_container()
    assert container.ports is not None
    actor = _actor()
    reviewer = AuthPrincipal(user_id="u-reviewer-1", tenant_id="t-1", name="评委", role="reviewer")
    eid, _, criteria, suppliers = await _configured_evaluation(container, actor)
    await container.evaluations.publish(actor, eid, idempotency_key="pub-3")
    # 推进到 pending 再 AI 评分
    await container.scoring.advance_to_pending(actor, eid)
    await container.scoring.start_ai_scoring(reviewer, eid)
    with pytest.raises(DomainError):
        await container.scoring.adjust_score(
            reviewer,
            eid,
            suppliers[0]["id"],
            criteria[0]["id"],
            human_score="88.00",
            adjustment_reason="",
            if_match=1,
        )
    adjusted = await container.scoring.adjust_score(
        reviewer,
        eid,
        suppliers[0]["id"],
        criteria[0]["id"],
        human_score="88.00",
        adjustment_reason="技术方案亮点加分",
        if_match=1,
    )
    assert adjusted["humanScore"] == "88.00"
    assert any(a.action == "score.adjusted" for a in container.ports.audits)
    ranking = await container.scoring.ranking(actor, eid)
    assert ranking["rows"]
    await container.scoring.confirm_scores(reviewer, eid, supplier_id=None, comment="确认")
    closed = await container.evaluations.close(actor, eid, "评标完成", idempotency_key="close-1")
    assert closed["status"] == "closed"
