"""Deterministic development data for the evaluation and supplier portal flow."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from app.domains.evaluations.entities import (
    EvaluationEntity,
    EvaluationMaterialEntity,
    PortalActivityEntity,
    PriceRoundEntity,
    ReviewSettingsEntity,
    RiskFindingEntity,
    ScoringCriterionEntity,
    SupplierEntity,
)
from app.domains.portal.security import hash_secret

if TYPE_CHECKING:
    from app.domains.evaluations.store import EvaluationStore


DEMO_EVALUATION_ID = "0190f4dd-0000-7000-8000-000000000601"
DEMO_PORTAL_INVITE_CODE = "EVAL-2026-001"
DEMO_TENANT_ID = "0190f4dd-0000-7000-8000-000000000002"
DEMO_ADMIN_USER_ID = "0190f4dd-0000-7000-8000-000000000001"


def _enabled() -> bool:
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    flag = os.getenv("DEMO_SEED_ENABLED", "false").strip().lower()
    return environment == "development" and flag in {"1", "true", "yes", "on"}


def seed_demo_evaluation_store(store: EvaluationStore) -> None:
    """Seed one published evaluation with a single-use, stable portal entry."""

    if not _enabled() or DEMO_EVALUATION_ID in store.evaluations:
        return

    now = datetime.now(UTC).replace(microsecond=0)
    tenant_id = os.getenv("DEMO_TENANT_ID", DEMO_TENANT_ID)
    admin_user_id = os.getenv("DEMO_ADMIN_USER_ID", DEMO_ADMIN_USER_ID)
    material_specs = [
        ("0190f4dd-0000-7000-8000-000000000611", "营业执照", "qualification", True),
        ("0190f4dd-0000-7000-8000-000000000612", "技术响应文件", "technical", True),
        ("0190f4dd-0000-7000-8000-000000000613", "报价清单", "commercial", True),
        ("0190f4dd-0000-7000-8000-000000000614", "同类项目案例", "qualification", False),
    ]
    materials = [
        EvaluationMaterialEntity(
            id=material_id,
            evaluation_id=DEMO_EVALUATION_ID,
            name=name,
            category=category,
            required=required,
            allowed_mime_types=[
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ],
            max_size_bytes=50 * 1024 * 1024,
            sort_order=index,
        )
        for index, (material_id, name, category, required) in enumerate(material_specs)
    ]
    criteria = [
        ScoringCriterionEntity(
            id="0190f4dd-0000-7000-8000-000000000631",
            evaluation_id=DEMO_EVALUATION_ID,
            name="技术方案完整性",
            category="technical",
            max_score=Decimal("100.00"),
            weight_percent=Decimal("60.00"),
            method="expert",
            description="架构、实施、质量和风险方案的完整性与可执行性",
            sort_order=0,
        ),
        ScoringCriterionEntity(
            id="0190f4dd-0000-7000-8000-000000000632",
            evaluation_id=DEMO_EVALUATION_ID,
            name="商务报价",
            category="commercial",
            max_score=Decimal("100.00"),
            weight_percent=Decimal("40.00"),
            method="formula",
            formula="min/quote*100",
            description="按有效最低报价计算价格得分",
            sort_order=1,
        ),
    ]
    supplier_specs = [
        ("0190f4dd-0000-7000-8000-000000000621", "深圳云启科技有限公司", "陈经理", "supplier-a@example.test"),
        ("0190f4dd-0000-7000-8000-000000000622", "鹏城数字技术有限公司", "刘经理", "supplier-b@example.test"),
        ("0190f4dd-0000-7000-8000-000000000623", "华南智联信息有限公司", "周经理", "supplier-c@example.test"),
    ]
    suppliers = [
        SupplierEntity(
            id=supplier_id,
            evaluation_id=DEMO_EVALUATION_ID,
            tenant_id=tenant_id,
            name=name,
            contact_name=contact_name,
            email=email,
            phone=f"1380000000{index}",
            status="invited",
            required_material_count=sum(1 for material in materials if material.required),
            invite_status="active",
            invite_expires_at=now + timedelta(days=30),
        )
        for index, (supplier_id, name, contact_name, email) in enumerate(supplier_specs, start=1)
    ]
    first_supplier = suppliers[0]
    first_supplier.invite_code_hash = hash_secret(DEMO_PORTAL_INVITE_CODE)
    first_supplier.invite_code_masked = "EVAL****-001"

    evaluation = EvaluationEntity(
        id=DEMO_EVALUATION_ID,
        tenant_id=tenant_id,
        source_bid_task_id="TASK-2026-001",
        project_name="2026年深圳市政务云平台采购项目",
        tender_no="SZGYY-2026-0312",
        tender_entity="深圳市政务服务数据管理局",
        budget_amount=Decimal("5000000.00"),
        currency="CNY",
        supplier_deadline=now + timedelta(days=7),
        evaluation_start_at=now + timedelta(days=8),
        evaluation_end_at=now + timedelta(days=14),
        status="collecting",
        current_step=2,
        progress_percent=25,
        assignee_id=admin_user_id,
        assignee_name=os.getenv("DEMO_ADMIN_NAME", "演示管理员"),
        description="覆盖供应商邀请、材料上传、报价、AI 初审、人工复核和报告生成的本地演示任务。",
        review_settings=ReviewSettingsEntity(
            multi_round_pricing=True,
            max_rounds=3,
            supplement_deadline_minutes=1440,
            allow_modify_before_deadline=True,
            notify_on_missing=True,
            close_submission_at_deadline=True,
        ),
        materials=materials,
        criteria=criteria,
        reviewer_ids=[admin_user_id],
        reviewer_names={admin_user_id: os.getenv("DEMO_ADMIN_NAME", "演示管理员")},
        suppliers=suppliers,
        version=1,
        created_at=now,
        updated_at=now,
    )
    store.save_evaluation(evaluation)
    store.invite_hash_index[first_supplier.invite_code_hash] = first_supplier.id
    store.save_round(
        PriceRoundEntity(
            id="0190f4dd-0000-7000-8000-000000000651",
            evaluation_id=DEMO_EVALUATION_ID,
            round_number=1,
            title="第一轮报价",
            opens_at=now - timedelta(hours=1),
            deadline=now + timedelta(days=2),
            status="open",
            eligible_supplier_ids=[supplier.id for supplier in suppliers],
            ranking_visible_to_supplier=True,
        )
    )
    store.save_risk(
        RiskFindingEntity(
            id="0190f4dd-0000-7000-8000-000000000641",
            evaluation_id=DEMO_EVALUATION_ID,
            supplier_id=suppliers[1].id,
            type="qualification_expiry",
            severity="warning",
            title="资质有效期临近评标截止时间",
            evidence=["供应商资质有效期字段需在正式评审前人工核验"],
            decision="pending",
            ai_confidence=0.82,
        )
    )
    store.add_activity(
        PortalActivityEntity(
            id="0190f4dd-0000-7000-8000-000000000661",
            evaluation_id=DEMO_EVALUATION_ID,
            supplier_id=first_supplier.id,
            action="invite_sent",
            summary="采购方已发送供应商专属邀请",
            occurred_at=now,
        )
    )


__all__ = [
    "DEMO_EVALUATION_ID",
    "DEMO_PORTAL_INVITE_CODE",
    "seed_demo_evaluation_store",
]
