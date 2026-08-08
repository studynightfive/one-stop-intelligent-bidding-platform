"""M6 ORM 模型。L0 在 models_registry 显式 import 后生成 Alembic 迁移。

MIGRATION-NOTE（供 L0）:
- 新增表：evaluation_tasks, evaluation_materials, scoring_criteria,
  evaluation_reviewers, evaluation_suppliers, supplier_invites,
  supplier_submissions, supplement_notices, price_rounds, quote_submissions,
  score_items, risk_findings, material_checks, evaluation_reports,
  portal_drafts, portal_activities, portal_sessions, evaluation_idempotency
- 金额 NUMERIC(18,2)；分数 NUMERIC(8,2)；权重 NUMERIC(5,2)
- 全表含 id(UUIDv7)/tenant_id/created_at/updated_at；可编辑表含 version
- 审计事件走 M4 audit；本域不建可 UPDATE/DELETE 的审计表
- upgrade/downgrade 风险：空库可顺序创建；生产无数据回填
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models_registry import Base


class EvaluationTaskModel(Base):
    __tablename__ = "evaluation_tasks"
    __table_args__ = (
        Index("ix_evaluation_tasks_tenant_status", "tenant_id", "status"),
        Index("ix_evaluation_tasks_tenant_assignee", "tenant_id", "assignee_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_bid_task_id: Mapped[str | None] = mapped_column(String(36))
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tender_no: Mapped[str] = mapped_column(String(128), nullable=False)
    tender_entity: Mapped[str] = mapped_column(String(255), nullable=False)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    supplier_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluation_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evaluation_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assignee_id: Mapped[str] = mapped_column(String(36), nullable=False)
    assignee_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    result_summary: Mapped[str | None] = mapped_column(Text)
    review_settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[str | None] = mapped_column(String(36))

    materials: Mapped[list[EvaluationMaterialModel]] = relationship(back_populates="evaluation")
    criteria: Mapped[list[ScoringCriterionModel]] = relationship(back_populates="evaluation")
    suppliers: Mapped[list[EvaluationSupplierModel]] = relationship(back_populates="evaluation")


class EvaluationMaterialModel(Base):
    __tablename__ = "evaluation_materials"
    __table_args__ = (Index("ix_evaluation_materials_eval", "evaluation_id", "sort_order"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allowed_mime_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    max_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    evaluation: Mapped[EvaluationTaskModel] = relationship(back_populates="materials")


class ScoringCriterionModel(Base):
    __tablename__ = "scoring_criteria"
    __table_args__ = (Index("ix_scoring_criteria_eval", "evaluation_id", "sort_order"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    max_score: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    weight_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    formula: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    evaluation: Mapped[EvaluationTaskModel] = relationship(back_populates="criteria")


class EvaluationReviewerModel(Base):
    __tablename__ = "evaluation_reviewers"
    __table_args__ = (UniqueConstraint("evaluation_id", "user_id", name="uq_evaluation_reviewer"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvaluationSupplierModel(Base):
    __tablename__ = "evaluation_suppliers"
    __table_args__ = (
        Index("ix_evaluation_suppliers_eval_status", "evaluation_id", "status"),
        UniqueConstraint("evaluation_id", "email", name="uq_evaluation_supplier_email"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="invited")
    submitted_material_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    required_material_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_quote: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    evaluation: Mapped[EvaluationTaskModel] = relationship(back_populates="suppliers")


class SupplierInviteModel(Base):
    __tablename__ = "supplier_invites"
    __table_args__ = (Index("ix_supplier_invites_hash", "invite_code_hash", unique=True),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("evaluation_suppliers.id"), nullable=False)
    invite_code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    invite_code_masked: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SupplierSubmissionModel(Base):
    __tablename__ = "supplier_submissions"
    __table_args__ = (UniqueConstraint("supplier_id", "material_id", name="uq_supplier_material_submission"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("evaluation_suppliers.id"), nullable=False)
    material_id: Mapped[str] = mapped_column(String(36), nullable=False)
    file_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SupplementNoticeModel(Base):
    __tablename__ = "supplement_notices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("evaluation_suppliers.id"), nullable=False)
    material_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PriceRoundModel(Base):
    __tablename__ = "price_rounds"
    __table_args__ = (UniqueConstraint("evaluation_id", "round_number", name="uq_price_round_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    eligible_supplier_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    ranking_visible_to_supplier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QuoteSubmissionModel(Base):
    __tablename__ = "quote_submissions"
    __table_args__ = (
        UniqueConstraint("round_id", "supplier_id", name="uq_quote_round_supplier"),
        Index("ix_quote_idempotency", "idempotency_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    round_id: Mapped[str] = mapped_column(ForeignKey("price_rounds.id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("evaluation_suppliers.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScoreItemModel(Base):
    __tablename__ = "score_items"
    __table_args__ = (UniqueConstraint("evaluation_id", "supplier_id", "criterion_id", name="uq_score_item"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    criterion_id: Mapped[str] = mapped_column(String(36), nullable=False)
    ai_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    ai_basis: Mapped[str | None] = mapped_column(Text)
    human_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    adjustment_reason: Mapped[str | None] = mapped_column(Text)
    final_score: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    adjusted_by_id: Mapped[str | None] = mapped_column(String(36))
    adjusted_by_name: Mapped[str | None] = mapped_column(String(128))
    adjusted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskFindingModel(Base):
    __tablename__ = "risk_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    ai_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    decision: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decided_by_id: Mapped[str | None] = mapped_column(String(36))
    decided_by_name: Mapped[str | None] = mapped_column(String(128))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MaterialCheckModel(Base):
    __tablename__ = "material_checks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvaluationReportModel(Base):
    __tablename__ = "evaluation_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_by_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_by_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PortalDraftModel(Base):
    __tablename__ = "portal_drafts"
    __table_args__ = (UniqueConstraint("supplier_id", name="uq_portal_draft_supplier"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("evaluation_suppliers.id"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    quote_draft: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PortalActivityModel(Base):
    __tablename__ = "portal_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("evaluation_suppliers.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PortalSessionModel(Base):
    __tablename__ = "portal_sessions"
    __table_args__ = (Index("ix_portal_sessions_token", "access_token_hash", unique=True),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluation_tasks.id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("evaluation_suppliers.id"), nullable=False)
    access_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvaluationIdempotencyModel(Base):
    __tablename__ = "evaluation_idempotency"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key", name="uq_evaluation_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    response_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
