"""Development-only bid data that exercises the full document-generation flow."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.domains.bids.entities import (
    BidMaterialEntity,
    BidReviewReportEntity,
    BidTaskAssignmentEntity,
    BidTaskEntity,
    TenderRequirementsEntity,
)

if TYPE_CHECKING:
    from app.domains.bids.store import BidStore


DEMO_TENANT_ID = "0190f4dd-0000-7000-8000-000000000002"
DEMO_ADMIN_USER_ID = "0190f4dd-0000-7000-8000-000000000001"
GENERATION_READY_TASK_ID = "TASK-2026-002"


def _enabled() -> bool:
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    flag = os.getenv("DEMO_SEED_ENABLED", "false").strip().lower()
    return environment == "development" and flag in {"1", "true", "yes", "on"}


def _at(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def seed_demo_bid_store(store: BidStore) -> None:
    """Seed stable task IDs shared with the front-end demo fixtures.

    The operation is disabled outside development and is idempotent so app
    factories and hot reloads cannot duplicate records.
    """
    if not _enabled() or GENERATION_READY_TASK_ID in store.tasks:
        return

    tenant_id = os.getenv("DEMO_TENANT_ID", DEMO_TENANT_ID)
    admin_user_id = os.getenv("DEMO_ADMIN_USER_ID", DEMO_ADMIN_USER_ID)
    now = _at("2026-08-04T10:00:00")
    task_rows = [
        (
            "TASK-2026-001",
            "2026年深圳市政务云平台采购项目",
            "SZGYY-2026-0312",
            "深圳市政务服务数据管理局",
            "2026-08-20T17:00:00",
            "material_prep",
            3,
            45,
            "张明远",
            ["云计算", "政务", "基础设施"],
        ),
        (
            GENERATION_READY_TASK_ID,
            "华南地区企业数字化转型咨询服务",
            "HNZX-2026-0089",
            "广东省工业互联网协会",
            "2026-08-15T17:00:00",
            "ai_review",
            6,
            80,
            "李雪琴",
            ["咨询", "数字化转型", "AI逐段生成"],
        ),
        (
            "TASK-2026-003",
            "某集团ERP系统升级项目",
            "GRP-ERP-2026-0156",
            "华润集团",
            "2026-07-30T17:00:00",
            "completed",
            7,
            100,
            "王建国",
            ["ERP", "企业信息化", "已完成"],
        ),
        (
            "TASK-2026-004",
            "智慧城市数据中台建设项目",
            "ZHCSSJ-2026-0078",
            "广州市天河区政务服务中心",
            "2026-09-05T17:00:00",
            "parsing",
            2,
            15,
            "张明远",
            ["智慧城市", "数据中台"],
        ),
        (
            "TASK-2026-005",
            "医疗机构信息化改造工程",
            "YLXX-2026-0234",
            "中山大学附属第一医院",
            "2026-08-28T17:00:00",
            "material_prep",
            5,
            60,
            "李雪琴",
            ["医疗", "信息化", "改造工程"],
        ),
    ]

    for index, row in enumerate(task_rows, start=1):
        task_id, project_name, tender_no, tender_entity, deadline, status, step, progress, assignee_name, tags = row
        store.save_task(
            BidTaskEntity(
                id=task_id,
                tenant_id=tenant_id,
                project_name=project_name,
                tender_no=tender_no,
                tender_entity=tender_entity,
                deadline=_at(deadline),
                status=status,
                current_step=step,
                progress_percent=progress,
                assignee_id=admin_user_id,
                assignee_name=assignee_name,
                tags=tags,
                description=f"{project_name}前端演示与接口联调任务。",
                tender_file_id=f"DEMO-TENDER-{index:03d}",
                tender_file_name=f"{tender_no}-招标文件.pdf",
                tender_mime_type="application/pdf",
                tender_size_bytes=2_048_000,
                tender_sha256=str(index) * 64,
                tender_scan_status="clean",
                tender_file_created_at=now,
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        store.save_assignment(
            BidTaskAssignmentEntity(
                id=f"DEMO-ASSIGNMENT-{index:03d}",
                tenant_id=tenant_id,
                task_id=task_id,
                user_id=admin_user_id,
                user_name="演示管理员",
                role_in_task="owner",
                assigned_at=now,
            )
        )

    store.save_requirements(
        GENERATION_READY_TASK_ID,
        TenderRequirementsEntity(
            tenant_id=tenant_id,
            task_id=GENERATION_READY_TASK_ID,
            project_info={
                "serviceScope": "企业数字化现状诊断、总体规划、实施路线设计与落地辅导",
                "deliveryPeriod": "合同签订后120日历天",
                "qualityGoal": "成果通过专家评审并形成可执行的分阶段建设蓝图",
            },
            qualification_requirements=[
                "具备有效营业执照和质量管理体系认证",
                "近三年具有同类数字化转型咨询项目经验",
            ],
            technical_requirements=[
                "给出业务、数据、应用与技术四层总体架构",
                "形成分阶段实施路线、关键里程碑和风险控制措施",
                "说明调研、诊断、方案设计、试点验证和推广方法",
                "技术响应内容必须逐条对应招标要求并提供依据",
            ],
            scoring_items=[
                {"name": "总体技术方案", "score": "35", "basis": "完整性、先进性与可实施性"},
                {"name": "实施与质量保障", "score": "25", "basis": "组织、进度、质量和风险机制"},
                {"name": "项目团队与业绩", "score": "20", "basis": "人员能力与同类经验"},
            ],
            disqualification_items=[
                {"name": "强制性技术条款", "basis": "不得出现负偏离"},
                {"name": "资质与业绩真实性", "basis": "不得提供虚假材料"},
            ],
        ),
    )

    for index, (name, category, requirement) in enumerate(
        [
            ("企业数字化现状诊断方案", "technical", "覆盖组织、流程、数据和系统现状"),
            ("总体架构与演进路线", "technical", "包含目标架构、阶段划分和里程碑"),
            ("项目实施与质量计划", "technical", "说明组织、进度、质量和风险保障"),
            ("近三年同类项目业绩", "qualification", "至少提供三个有效案例"),
        ],
        start=1,
    ):
        store.save_material(
            BidMaterialEntity(
                id=f"DEMO-MATERIAL-{index:03d}",
                tenant_id=tenant_id,
                task_id=GENERATION_READY_TASK_ID,
                name=name,
                category=category,
                requirement=requirement,
                required=True,
                sort_order=index,
                source="library",
                source_id=f"DEMO-LIBRARY-{index:03d}",
                status="have",
                version=1,
                created_at=now,
                updated_at=now,
            )
        )

    store.save_review_report(
        BidReviewReportEntity(
            id="DEMO-REVIEW-002",
            tenant_id=tenant_id,
            task_id=GENERATION_READY_TASK_ID,
            status="succeeded",
            summary="AI审核已完成；未发现阻止文档生成的高风险问题。",
            counts={"error": 0, "warning": 2, "info": 3},
            findings=[],
            job_id="DEMO-REVIEW-JOB-002",
            completed_at=now,
            created_at=now,
            updated_at=now,
            version=1,
        )
    )
