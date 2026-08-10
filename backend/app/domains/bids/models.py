"""M5 ORM 模型（仅 bids 主表；documents 子表见 ``app.domains.documents.models``）。

MIGRATION-NOTE（供 L0）:
- 新增表：bid_tasks, bid_task_assignments, bid_tender_requirements,
  bid_materials, bid_review_reports, bid_review_findings, bid_idempotency,
  bid_job_bindings
- bid_tasks:
  - id (UUIDv7, PK)
  - tenant_id (UUID, indexed)
  - project_name (varchar(255))
  - tender_no (varchar(128))
  - tender_entity (varchar(255))
  - deadline (timestamptz)
  - status (varchar(32) – draft|parsing|material_prep|ai_review|pending_output|completed|archived|failed)
  - current_step (int, default 1)
  - progress_percent (int, default 0)
  - assignee_id (UUID)
  - assignee_name (varchar(128))
  - tags (jsonb, list[str], default [])
  - description (text, nullable)
  - tender_file_id (UUID, nullable)
  - tender_file_name (varchar(255), nullable)
  - tender_mime_type, tender_size_bytes, tender_sha256, tender_scan_status
  - tender_file_created_at, tender_preview_url, tender_download_url
  - linked_evaluation_id (UUID, nullable)
  - archived_reason (text, nullable)
  - failed_stage (varchar(32), nullable; 失败后仅允许重试该阶段)
  - version (int, default 1)
  - created_at / updated_at (timestamptz)
- bid_task_assignments:
  - id (UUIDv7, PK)
  - tenant_id (UUID, indexed)
  - task_id (UUID, FK -> bid_tasks.id)
  - user_id (UUID)
  - user_name (varchar(128))
  - role_in_task (varchar(16) – owner|collaborator|reviewer)
  - assigned_at (timestamptz)
  - UNIQUE(task_id, user_id)
- bid_tender_requirements:
  - id (UUIDv7, PK)
  - tenant_id (UUID, indexed)
  - task_id (UUID, UNIQUE FK -> bid_tasks.id)
  - project_info (jsonb, default {})
  - scoring_items (jsonb, default [])
  - disqualification_items (jsonb, default [])
  - qualification_requirements (jsonb, default [])
  - technical_requirements (jsonb, default [])
  - version (int, default 1)
  - updated_at (timestamptz)
- bid_materials:
  - id (UUIDv7, PK)
  - tenant_id (UUID, indexed)
  - task_id (UUID, FK -> bid_tasks.id)
  - name (varchar(255))
  - category (varchar(32))
  - requirement (text, default '')
  - required (boolean, default true)
  - sort_order (int, default 0)
  - source (varchar(16) – qualification|fragment|upload|template|manual)
  - source_id (UUID, nullable)
  - match_confidence (numeric(5,4), nullable)
  - file_id (UUID, nullable)
  - file_name (varchar(255), nullable)
  - mime_type (varchar(128), nullable)
  - size_bytes (bigint, default 0)
  - sha256 (varchar(64), nullable)
  - file_scan_status, file_created_at, file_preview_url, file_download_url
  - status (varchar(16), default 'pending')
  - version (int, default 1)
  - created_at / updated_at (timestamptz)
  - deleted_at (timestamptz, nullable; soft delete)
- bid_review_reports:
  - id (UUIDv7, PK)
  - tenant_id (UUID, indexed)
  - task_id (UUID, FK -> bid_tasks.id)
  - job_id (UUID, nullable)
  - status (varchar(16) – queued|running|succeeded|failed|cancelled)
  - summary (text, default '')
  - counts (jsonb, default {error:0, warning:0, info:0})
  - completed_at (timestamptz, nullable)
  - version (int, default 1)
  - created_at / updated_at (timestamptz)
- bid_review_findings:
  - id (UUIDv7, PK)
  - tenant_id (UUID, indexed)
  - report_id (UUID, FK -> bid_review_reports.id)
  - task_id (UUID, indexed)
  - type (varchar(16) – signature|price|content|consistency)
  - severity (varchar(16) – info|warning|high|critical)
  - title (varchar(255))
  - description (text, default '')
  - file_id (UUID)
  - page (int, nullable)
  - excerpt (text, nullable)
  - suggestion (text, default '')
  - decision (varchar(16) – pending|accepted|ignored|modified, default pending)
  - decision_comment (text, nullable)
  - decided_by_id (UUID, nullable)
  - decided_by_name (varchar(128), nullable)
  - decided_at (timestamptz, nullable)
  - version (int, default 1)
  - created_at / updated_at (timestamptz)
- bid_idempotency:
  - key (varchar(512), PK; tenant + actor + aggregate + action + client key)
  - tenant_id (UUID, indexed)
  - response_json (jsonb)
  - created_at (timestamptz)
- bid_job_bindings:
  - job_id (UUID, PK)
  - tenant_id (UUID, indexed)
  - task_id (UUID, indexed, FK -> bid_tasks.id)
  - action (varchar(64))
  - input_json (jsonb; 原始文件/材料/执行人/生成范围绑定)
  - outcome (varchar(16), nullable; succeeded|failed)
  - result_json (jsonb, nullable; terminal callback replay value)
  - completed_at (timestamptz, nullable)
  - created_at (timestamptz)
- 索引组合：
  - bid_tasks(tenant_id, status)
  - bid_tasks(tenant_id, assignee_id)
  - bid_tasks(tenant_id, deadline)
  - bid_materials(tenant_id, task_id, sort_order)
  - bid_review_reports(tenant_id, task_id, created_at)
  - bid_review_findings(tenant_id, task_id, severity, decision)
- 软删除：演示阶段不启用；列表默认只返回 status != 'archived' 的任务。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models_registry import Base


class BidTaskModel(Base):
    __tablename__ = "bid_tasks"
    __table_args__ = (
        Index("ix_bid_tasks_tenant_status", "tenant_id", "status"),
        Index("ix_bid_tasks_tenant_assignee", "tenant_id", "assignee_id"),
        Index("ix_bid_tasks_tenant_deadline", "tenant_id", "deadline"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tender_no: Mapped[str] = mapped_column(String(128), nullable=False)
    tender_entity: Mapped[str] = mapped_column(String(255), nullable=False)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assignee_id: Mapped[str] = mapped_column(String(36), nullable=False)
    assignee_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    description: Mapped[str | None] = mapped_column(Text)
    tender_file_id: Mapped[str | None] = mapped_column(String(36))
    tender_file_name: Mapped[str | None] = mapped_column(String(255))
    tender_mime_type: Mapped[str | None] = mapped_column(String(128))
    tender_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tender_sha256: Mapped[str | None] = mapped_column(String(64))
    tender_scan_status: Mapped[str | None] = mapped_column(String(16))
    tender_file_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tender_preview_url: Mapped[str | None] = mapped_column(Text)
    tender_download_url: Mapped[str | None] = mapped_column(Text)
    linked_evaluation_id: Mapped[str | None] = mapped_column(String(36))
    archived_reason: Mapped[str | None] = mapped_column(Text)
    failed_stage: Mapped[str | None] = mapped_column(String(32))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BidTaskAssignmentModel(Base):
    __tablename__ = "bid_task_assignments"
    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_bid_task_assignment"),
        Index("ix_bid_task_assignments_tenant", "tenant_id", "task_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("bid_tasks.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role_in_task: Mapped[str] = mapped_column(String(16), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BidTenderRequirementModel(Base):
    __tablename__ = "bid_tender_requirements"
    __table_args__ = (Index("ix_bid_tender_requirements_tenant", "tenant_id", "task_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("bid_tasks.id"), unique=True, nullable=False)
    project_info: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    scoring_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    disqualification_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    qualification_requirements: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    technical_requirements: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BidMaterialModel(Base):
    __tablename__ = "bid_materials"
    __table_args__ = (Index("ix_bid_materials_tenant_task", "tenant_id", "task_id", "sort_order"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("bid_tasks.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    requirement: Mapped[str] = mapped_column(Text, nullable=False, default="")
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    source_id: Mapped[str | None] = mapped_column(String(36))
    match_confidence: Mapped[float | None] = mapped_column(Float)
    file_id: Mapped[str | None] = mapped_column(String(36))
    file_name: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sha256: Mapped[str | None] = mapped_column(String(64))
    file_scan_status: Mapped[str | None] = mapped_column(String(16))
    file_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    file_preview_url: Mapped[str | None] = mapped_column(Text)
    file_download_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BidReviewReportModel(Base):
    __tablename__ = "bid_review_reports"
    __table_args__ = (Index("ix_bid_review_reports_tenant_task", "tenant_id", "task_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("bid_tasks.id"), nullable=False)
    job_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BidReviewFindingModel(Base):
    __tablename__ = "bid_review_findings"
    __table_args__ = (
        Index(
            "ix_bid_review_findings_tenant_task",
            "tenant_id",
            "task_id",
            "severity",
            "decision",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("bid_review_reports.id"), nullable=False)
    task_id: Mapped[str] = mapped_column(ForeignKey("bid_tasks.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    file_id: Mapped[str] = mapped_column(String(36), nullable=False)
    page: Mapped[int | None] = mapped_column(Integer)
    excerpt: Mapped[str | None] = mapped_column(Text)
    suggestion: Mapped[str] = mapped_column(Text, nullable=False, default="")
    decision: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    decision_comment: Mapped[str | None] = mapped_column(Text)
    decided_by_id: Mapped[str | None] = mapped_column(String(36))
    decided_by_name: Mapped[str | None] = mapped_column(String(128))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BidIdempotencyModel(Base):
    __tablename__ = "bid_idempotency"
    __table_args__ = (Index("ix_bid_idempotency_tenant", "tenant_id"),)

    key: Mapped[str] = mapped_column(String(512), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    response_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BidJobBindingModel(Base):
    __tablename__ = "bid_job_bindings"
    __table_args__ = (Index("ix_bid_job_bindings_tenant_task", "tenant_id", "task_id"),)

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("bid_tasks.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    outcome: Mapped[str | None] = mapped_column(String(16))
    result_json: Mapped[Any | None] = mapped_column(JSON)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
