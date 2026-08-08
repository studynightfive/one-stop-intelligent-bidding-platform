"""M6 领域实体（内存仓储与服务层使用；与 ORM 字段对齐）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass
class ReviewSettingsEntity:
    multi_round_pricing: bool = False
    max_rounds: int = 1
    supplement_deadline_minutes: int = 1440
    allow_modify_before_deadline: bool = True
    notify_on_missing: bool = True
    close_submission_at_deadline: bool = True


@dataclass
class EvaluationMaterialEntity:
    id: str
    evaluation_id: str
    name: str
    category: str
    required: bool
    allowed_mime_types: list[str]
    max_size_bytes: int
    sort_order: int


@dataclass
class ScoringCriterionEntity:
    id: str
    evaluation_id: str
    name: str
    category: str
    max_score: Decimal
    weight_percent: Decimal
    method: str
    description: str
    sort_order: int
    formula: str | None = None


@dataclass
class SupplierEntity:
    id: str
    evaluation_id: str
    tenant_id: str
    name: str
    contact_name: str
    email: str
    status: str
    required_material_count: int
    submitted_material_count: int = 0
    phone: str | None = None
    current_quote: Decimal | None = None
    submitted_at: datetime | None = None
    invite_code_hash: str | None = None
    invite_code_masked: str | None = None
    invite_status: str = "active"  # active|used|revoked|expired
    invite_expires_at: datetime | None = None
    invite_raw_once: str | None = None  # 仅创建/轮换时短暂持有


@dataclass
class SupplierSubmissionEntity:
    id: str
    evaluation_id: str
    supplier_id: str
    material_id: str
    file_id: str
    status: str  # draft|submitted|replaced
    version: int = 1
    submitted_at: datetime | None = None
    replaced_at: datetime | None = None


@dataclass
class SupplementNoticeEntity:
    id: str
    evaluation_id: str
    supplier_id: str
    material_ids: list[str]
    message: str
    deadline: datetime
    status: str
    sent_at: datetime
    responded_at: datetime | None = None


@dataclass
class PriceRoundEntity:
    id: str
    evaluation_id: str
    round_number: int
    title: str
    opens_at: datetime
    deadline: datetime
    status: str
    eligible_supplier_ids: list[str]
    ranking_visible_to_supplier: bool
    version: int = 1


@dataclass
class QuoteSubmissionEntity:
    id: str
    round_id: str
    evaluation_id: str
    supplier_id: str
    amount: Decimal
    currency: str
    submitted_at: datetime
    version: int = 1
    idempotency_key: str | None = None


@dataclass
class ScoreItemEntity:
    evaluation_id: str
    supplier_id: str
    criterion_id: str
    final_score: Decimal
    version: int = 1
    ai_score: Decimal | None = None
    ai_basis: str | None = None
    human_score: Decimal | None = None
    adjustment_reason: str | None = None
    adjusted_by_id: str | None = None
    adjusted_by_name: str | None = None
    adjusted_at: datetime | None = None
    confirmed: bool = False


@dataclass
class RiskFindingEntity:
    id: str
    evaluation_id: str
    supplier_id: str
    type: str
    severity: str
    title: str
    evidence: list[str]
    decision: str
    version: int = 1
    ai_confidence: float | None = None
    decision_reason: str | None = None
    decided_by_id: str | None = None
    decided_by_name: str | None = None
    decided_at: datetime | None = None


@dataclass
class MaterialCheckEntity:
    id: str
    evaluation_id: str
    status: str
    rows: list[dict[str, Any]]
    completed_at: datetime | None = None


@dataclass
class EvaluationReportEntity:
    id: str
    evaluation_id: str
    format: str
    version_number: int
    file_id: str
    created_by_id: str
    created_by_name: str
    created_at: datetime


@dataclass
class PortalDraftEntity:
    supplier_id: str
    evaluation_id: str
    note: str | None = None
    quote_draft: Decimal | None = None
    saved_at: datetime | None = None
    version: int = 1


@dataclass
class PortalActivityEntity:
    id: str
    evaluation_id: str
    supplier_id: str
    action: str
    summary: str
    occurred_at: datetime


@dataclass
class PortalSessionEntity:
    token_id: str
    access_token: str
    supplier_id: str
    evaluation_id: str
    tenant_id: str
    expires_at: datetime
    revoked: bool = False
    refresh_token: str | None = None
    refresh_expires_at: datetime | None = None


@dataclass
class EvaluationEntity:
    id: str
    tenant_id: str
    project_name: str
    tender_no: str
    tender_entity: str
    budget_amount: Decimal
    currency: str
    supplier_deadline: datetime
    evaluation_start_at: datetime
    evaluation_end_at: datetime
    status: str
    current_step: int
    progress_percent: int
    assignee_id: str
    assignee_name: str
    version: int
    created_at: datetime
    updated_at: datetime
    source_bid_task_id: str | None = None
    description: str | None = None
    result_summary: str | None = None
    review_settings: ReviewSettingsEntity = field(default_factory=ReviewSettingsEntity)
    materials: list[EvaluationMaterialEntity] = field(default_factory=list)
    criteria: list[ScoringCriterionEntity] = field(default_factory=list)
    reviewer_ids: list[str] = field(default_factory=list)
    reviewer_names: dict[str, str] = field(default_factory=dict)
    suppliers: list[SupplierEntity] = field(default_factory=list)
    latest_job_ids: list[str] = field(default_factory=list)

    @property
    def supplier_count(self) -> int:
        return len(self.suppliers)

    @property
    def risk_count(self) -> int:
        return 0  # 由 store 聚合覆盖
