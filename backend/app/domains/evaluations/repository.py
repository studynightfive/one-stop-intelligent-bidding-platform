"""SQLAlchemy 仓储骨架：待 L0 迁移 + M4 AsyncSession 后启用。

当前默认仍使用 EvaluationStore（内存）。本模块提供：
1. 仓储协议别名
2. 从 ORM 行映射到领域实体的转换函数（便于后续落库）
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.domains.evaluations.entities import EvaluationEntity, ReviewSettingsEntity
from app.domains.evaluations.store import EvaluationStore


def default_repository() -> EvaluationStore:
    return EvaluationStore()


def evaluation_from_orm_row(row: Any) -> EvaluationEntity:
    """将 EvaluationTaskModel 行转为领域实体（关系集合需调用方另行装填）。"""
    settings_raw = getattr(row, "review_settings", {}) or {}
    settings = ReviewSettingsEntity(
        multi_round_pricing=bool(settings_raw.get("multiRoundPricing", False)),
        max_rounds=int(settings_raw.get("maxRounds", 1)),
        supplement_deadline_minutes=int(settings_raw.get("supplementDeadlineMinutes", 1440)),
        allow_modify_before_deadline=bool(settings_raw.get("allowModifyBeforeDeadline", True)),
        notify_on_missing=bool(settings_raw.get("notifyOnMissing", True)),
        close_submission_at_deadline=bool(settings_raw.get("closeSubmissionAtDeadline", True)),
    )
    return EvaluationEntity(
        id=str(row.id),
        tenant_id=str(row.tenant_id),
        source_bid_task_id=str(row.source_bid_task_id) if row.source_bid_task_id else None,
        project_name=row.project_name,
        tender_no=row.tender_no,
        tender_entity=row.tender_entity,
        budget_amount=Decimal(str(row.budget_amount)),
        currency=row.currency,
        supplier_deadline=row.supplier_deadline,
        evaluation_start_at=row.evaluation_start_at,
        evaluation_end_at=row.evaluation_end_at,
        status=row.status,
        current_step=int(row.current_step),
        progress_percent=int(row.progress_percent),
        assignee_id=str(row.assignee_id),
        assignee_name=row.assignee_name,
        description=row.description,
        result_summary=row.result_summary,
        review_settings=settings,
        version=int(row.version),
        created_at=row.created_at or datetime.now(UTC),
        updated_at=row.updated_at or datetime.now(UTC),
    )


class SqlAlchemyEvaluationRepository:
    """占位：需要 AsyncSession。合并 M4 后实现 CRUD，替换 EvaluationStore。"""

    def __init__(self, session: Any) -> None:
        self.session = session
        raise NotImplementedError(
            "SqlAlchemyEvaluationRepository 需 L0 迁移 upgrade 且 M4 提供 AsyncSession 后启用。"
            "当前请使用 default_repository()/EvaluationStore。"
        )
