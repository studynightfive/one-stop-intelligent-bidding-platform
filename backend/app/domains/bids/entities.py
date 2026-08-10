"""M5 领域实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TenderRequirementsEntity:
    tenant_id: str
    task_id: str
    project_info: dict[str, str] = field(default_factory=dict)
    scoring_items: list[dict[str, str]] = field(default_factory=list)
    disqualification_items: list[dict[str, str]] = field(default_factory=list)
    qualification_requirements: list[str] = field(default_factory=list)
    technical_requirements: list[str] = field(default_factory=list)
    version: int = 1


@dataclass
class BidMaterialEntity:
    id: str
    tenant_id: str
    task_id: str
    name: str
    category: str
    requirement: str
    required: bool
    sort_order: int
    source: str = "manual"
    source_id: str | None = None
    match_confidence: float | None = None
    file_id: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    size_bytes: int = 0
    sha256: str | None = None
    file_scan_status: str | None = None
    file_created_at: datetime | None = None
    file_preview_url: str | None = None
    file_download_url: str | None = None
    status: str = "pending"
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass
class BidTaskAssignmentEntity:
    id: str
    tenant_id: str
    task_id: str
    user_id: str
    user_name: str
    role_in_task: str  # owner | collaborator | reviewer
    assigned_at: datetime


@dataclass
class BidReviewFindingEntity:
    id: str
    tenant_id: str
    report_id: str
    task_id: str
    type: str  # signature | price | content | consistency
    severity: str  # info | warning | high | critical
    title: str
    description: str
    file_id: str
    page: int | None = None
    excerpt: str | None = None
    suggestion: str = ""
    decision: str = "pending"  # pending | accepted | ignored | modified
    decision_comment: str | None = None
    decided_by_id: str | None = None
    decided_by_name: str | None = None
    decided_at: datetime | None = None
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class BidReviewReportEntity:
    id: str
    tenant_id: str
    task_id: str
    status: str  # queued | running | succeeded | failed | cancelled
    summary: str = ""
    counts: dict[str, int] = field(default_factory=lambda: {"error": 0, "warning": 0, "info": 0})
    findings: list[BidReviewFindingEntity] = field(default_factory=list)
    job_id: str | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1


@dataclass
class BidTaskEntity:
    id: str
    tenant_id: str
    project_name: str
    tender_no: str
    tender_entity: str
    deadline: datetime
    status: str
    current_step: int
    progress_percent: int
    assignee_id: str
    assignee_name: str
    tags: list[str] = field(default_factory=list)
    description: str | None = None
    tender_file_id: str | None = None
    tender_file_name: str | None = None
    tender_mime_type: str | None = None
    tender_size_bytes: int = 0
    tender_sha256: str | None = None
    tender_scan_status: str | None = None
    tender_file_created_at: datetime | None = None
    tender_preview_url: str | None = None
    tender_download_url: str | None = None
    linked_evaluation_id: str | None = None
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_reason: str | None = None
    failed_stage: str | None = None

    # 附属关联
    assignments: list[BidTaskAssignmentEntity] = field(default_factory=list)
    materials: list[BidMaterialEntity] = field(default_factory=list)
    requirements: TenderRequirementsEntity | None = None
    latest_review: BidReviewReportEntity | None = None

    @property
    def material_summary(self) -> dict[str, int]:
        total = len(self.materials)
        have = sum(1 for m in self.materials if m.status in ("have", "uploaded", "template"))
        missing = sum(1 for m in self.materials if m.status == "missing")
        return {"total": total, "have": have, "missing": missing}
