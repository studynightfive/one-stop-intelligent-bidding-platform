"""M5 内存仓储（与 M6 EvaluationStore 风格一致）。"""

from __future__ import annotations

import asyncio
import copy
from datetime import UTC, datetime, timedelta
from typing import Any

from app.domains.bids.entities import (
    BidMaterialEntity,
    BidReviewFindingEntity,
    BidReviewReportEntity,
    BidTaskAssignmentEntity,
    BidTaskEntity,
    TenderRequirementsEntity,
)
from app.domains.bids.errors import conflict, not_found


class BidStore:
    def __init__(self) -> None:
        self.tasks: dict[str, BidTaskEntity] = {}
        self.assignments: dict[str, BidTaskAssignmentEntity] = {}
        self.materials: dict[str, BidMaterialEntity] = {}
        self.requirements: dict[tuple[str, str], TenderRequirementsEntity] = {}
        self.review_reports: dict[str, BidReviewReportEntity] = {}
        self.review_findings: dict[str, BidReviewFindingEntity] = {}
        self.idempotency: dict[str, Any] = {}
        self.job_bindings: dict[str, tuple[str, str, str, dict[str, Any]]] = {}
        self.latest_jobs: dict[tuple[str, str, str], str] = {}
        self.job_results: dict[str, tuple[str, str, str, Any]] = {}
        self.job_result_lock = asyncio.Lock()
        self.operation_locks: dict[str, asyncio.Lock] = {}

    def operation_lock(self, key: str) -> asyncio.Lock:
        lock = self.operation_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self.operation_locks[key] = lock
        return lock

    # ---- 任务 ----
    def save_task(self, entity: BidTaskEntity) -> BidTaskEntity:
        self.tasks[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def get_task(self, task_id: str, *, tenant_id: str) -> BidTaskEntity:
        stored = self.tasks.get(task_id)
        task = copy.deepcopy(stored) if stored is not None else None
        if task is None or task.tenant_id != tenant_id:
            raise not_found("投标任务不存在", taskId=task_id)
        # 装填关联
        self._populate(task)
        return copy.deepcopy(task)

    def _populate(self, task: BidTaskEntity) -> None:
        task.assignments = [
            copy.deepcopy(a)
            for a in self.assignments.values()
            if a.tenant_id == task.tenant_id and a.task_id == task.id
        ]
        task.materials = [
            copy.deepcopy(m)
            for m in self.materials.values()
            if m.tenant_id == task.tenant_id and m.task_id == task.id and m.deleted_at is None
        ]
        minimum = datetime.min.replace(tzinfo=UTC)
        task.materials.sort(key=lambda m: (m.sort_order, m.created_at or minimum))
        task.requirements = copy.deepcopy(self.requirements.get((task.tenant_id, task.id)))
        reports = [r for r in self.review_reports.values() if r.tenant_id == task.tenant_id and r.task_id == task.id]
        if reports:
            reports.sort(key=lambda r: r.created_at or minimum, reverse=True)
            latest = copy.deepcopy(reports[0])
            latest.findings = [
                copy.deepcopy(finding)
                for finding in self.review_findings.values()
                if finding.tenant_id == task.tenant_id and finding.task_id == task.id and finding.report_id == latest.id
            ]
            task.latest_review = latest

    def list_tasks(
        self,
        *,
        tenant_id: str,
        keyword: str | None = None,
        status: str | None = None,
        assignee_id: str | None = None,
        quick_filter: str | None = None,
        include_archived: bool = False,
    ) -> list[BidTaskEntity]:
        items = [copy.deepcopy(t) for t in self.tasks.values() if t.tenant_id == tenant_id]
        if not include_archived and status != "archived":
            items = [t for t in items if t.status != "archived"]
        if status:
            items = [t for t in items if t.status == status]
        if assignee_id:
            items = [t for t in items if t.assignee_id == assignee_id]
        if quick_filter:
            q = quick_filter.lower()
            if q == "my":
                # quickFilter=my 由路由层转成 assigneeId 过滤；此处退化为不过滤
                pass
            elif q == "overdue":
                now = datetime.now(UTC)
                items = [t for t in items if t.deadline < now and t.status not in {"completed", "archived", "failed"}]
            elif q == "due_soon":
                now = datetime.now(UTC)
                items = [
                    t
                    for t in items
                    if now <= t.deadline <= now + timedelta(days=3)
                    and t.status not in {"completed", "archived", "failed"}
                ]
        if keyword:
            kw = keyword.lower()
            items = [
                t
                for t in items
                if kw in t.project_name.lower() or kw in t.tender_no.lower() or kw in t.tender_entity.lower()
            ]
        minimum = datetime.min.replace(tzinfo=UTC)
        items.sort(key=lambda t: t.updated_at or minimum, reverse=True)
        for t in items:
            self._populate(t)
        return items

    # ---- 分配 ----
    def save_assignment(self, entity: BidTaskAssignmentEntity) -> BidTaskAssignmentEntity:
        # 同 task+user 已存在则覆盖
        for key, existing in list(self.assignments.items()):
            if existing.task_id == entity.task_id and existing.user_id == entity.user_id:
                del self.assignments[key]
        self.assignments[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def remove_assignment(self, *, task_id: str, user_id: str) -> bool:
        for key, existing in list(self.assignments.items()):
            if existing.task_id == task_id and existing.user_id == user_id:
                del self.assignments[key]
                return True
        return False

    # ---- 材料 ----
    def save_material(self, entity: BidMaterialEntity) -> BidMaterialEntity:
        self.materials[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def get_material(self, material_id: str, *, tenant_id: str) -> BidMaterialEntity:
        material = self.materials.get(material_id)
        if material is None or material.tenant_id != tenant_id or material.deleted_at is not None:
            raise not_found("材料不存在", materialId=material_id)
        return copy.deepcopy(material)

    def remove_material(self, material_id: str, *, tenant_id: str) -> None:
        material = self.materials.get(material_id)
        if material is None or material.tenant_id != tenant_id or material.deleted_at is not None:
            raise not_found("材料不存在", materialId=material_id)
        material.deleted_at = datetime.now(UTC)
        material.updated_at = material.deleted_at
        self.materials[material_id] = copy.deepcopy(material)

    def list_materials(
        self,
        *,
        tenant_id: str,
        task_id: str,
        category: str | None = None,
        status: str | None = None,
        required: bool | None = None,
    ) -> list[BidMaterialEntity]:
        items = [
            copy.deepcopy(m)
            for m in self.materials.values()
            if m.tenant_id == tenant_id and m.task_id == task_id and m.deleted_at is None
        ]
        if category:
            items = [m for m in items if m.category == category]
        if status:
            items = [m for m in items if m.status == status]
        if required is not None:
            items = [m for m in items if m.required is required]
        minimum = datetime.min.replace(tzinfo=UTC)
        items.sort(key=lambda m: (m.sort_order, m.created_at or minimum))
        return items

    # ---- 需求 ----
    def save_requirements(self, task_id: str, entity: TenderRequirementsEntity) -> TenderRequirementsEntity:
        if entity.task_id != task_id:
            raise ValueError("requirements task_id mismatch")
        self.requirements[(entity.tenant_id, task_id)] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def get_requirements(self, task_id: str, *, tenant_id: str) -> TenderRequirementsEntity | None:
        entity = self.requirements.get((tenant_id, task_id))
        return copy.deepcopy(entity) if entity else None

    # ---- 审核 ----
    def save_review_report(self, entity: BidReviewReportEntity) -> BidReviewReportEntity:
        self.review_reports[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def remove_review_report(self, report_id: str, *, tenant_id: str) -> None:
        report = self.review_reports.get(report_id)
        if report is not None and report.tenant_id == tenant_id:
            del self.review_reports[report_id]

    def get_review_report_by_job(self, job_id: str, *, tenant_id: str) -> BidReviewReportEntity:
        for report in self.review_reports.values():
            if report.tenant_id == tenant_id and report.job_id == job_id:
                return copy.deepcopy(report)
        raise not_found("审核任务不存在", jobId=job_id)

    def latest_review_for_task(self, task_id: str, *, tenant_id: str) -> BidReviewReportEntity | None:
        items = [r for r in self.review_reports.values() if r.tenant_id == tenant_id and r.task_id == task_id]
        if not items:
            return None
        minimum = datetime.min.replace(tzinfo=UTC)
        items.sort(key=lambda r: r.created_at or minimum, reverse=True)
        latest = copy.deepcopy(items[0])
        latest.findings = [
            copy.deepcopy(f)
            for f in self.review_findings.values()
            if f.tenant_id == tenant_id and f.task_id == task_id and f.report_id == latest.id
        ]
        return latest

    def save_finding(self, entity: BidReviewFindingEntity) -> BidReviewFindingEntity:
        self.review_findings[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def get_finding(self, finding_id: str, *, tenant_id: str) -> BidReviewFindingEntity:
        finding = self.review_findings.get(finding_id)
        if finding is None or finding.tenant_id != tenant_id:
            raise not_found("审核发现不存在", findingId=finding_id)
        return copy.deepcopy(finding)

    # ---- 幂等 ----
    def remember_idempotency(self, key: str, value: Any) -> None:
        self.idempotency[key] = copy.deepcopy(value)

    def get_idempotency(self, key: str) -> Any | None:
        value = self.idempotency.get(key)
        return copy.deepcopy(value) if value is not None else None

    # ---- 异步 Job 与聚合绑定 ----
    def remember_job(
        self,
        job_id: str,
        *,
        tenant_id: str,
        task_id: str,
        action: str,
        input_data: dict[str, Any] | None = None,
    ) -> None:
        self.job_bindings[job_id] = (tenant_id, task_id, action, copy.deepcopy(input_data or {}))
        self.latest_jobs[(tenant_id, task_id, action)] = job_id

    def assert_job(self, job_id: str, *, tenant_id: str, task_id: str, action: str) -> None:
        binding = self.job_bindings.get(job_id)
        if binding is None:
            raise not_found("异步任务不存在", jobId=job_id)
        if binding[:3] != (tenant_id, task_id, action):
            raise conflict("异步结果与任务或动作不匹配", jobId=job_id)

    def assert_latest_job(self, job_id: str, *, tenant_id: str, task_id: str, action: str) -> None:
        latest_job_id = self.latest_jobs.get((tenant_id, task_id, action))
        if latest_job_id != job_id:
            raise conflict(
                "异步任务已被更新任务取代",
                jobId=job_id,
                latestJobId=latest_job_id,
                action=action,
            )

    def get_job_action(self, job_id: str, *, tenant_id: str, task_id: str) -> str:
        binding = self.job_bindings.get(job_id)
        if binding is None:
            raise not_found("异步任务不存在", jobId=job_id)
        if binding[:2] != (tenant_id, task_id):
            raise conflict("异步结果与任务不匹配", jobId=job_id)
        return binding[2]

    def get_job_input(self, job_id: str, *, tenant_id: str, task_id: str, action: str) -> dict[str, Any]:
        self.assert_job(job_id, tenant_id=tenant_id, task_id=task_id, action=action)
        return copy.deepcopy(self.job_bindings[job_id][3])

    def get_job_result(self, job_id: str, *, tenant_id: str, task_id: str, outcome: str) -> Any | None:
        stored = self.job_results.get(job_id)
        if stored is None:
            return None
        stored_tenant, stored_task, stored_outcome, value = stored
        if (stored_tenant, stored_task) != (tenant_id, task_id):
            raise conflict("异步结果与任务不匹配", jobId=job_id)
        if stored_outcome != outcome:
            raise conflict("异步任务已有相反的终态结果", jobId=job_id, terminalOutcome=stored_outcome)
        return copy.deepcopy(value)

    def remember_job_result(
        self,
        job_id: str,
        *,
        tenant_id: str,
        task_id: str,
        outcome: str,
        value: Any,
    ) -> None:
        existing = self.job_results.get(job_id)
        if existing is not None and existing[:3] != (tenant_id, task_id, outcome):
            raise conflict("异步任务已有相反的终态结果", jobId=job_id, terminalOutcome=existing[2])
        self.job_results[job_id] = (tenant_id, task_id, outcome, copy.deepcopy(value))


def default_repository() -> BidStore:
    return BidStore()


def task_from_orm_row(row: Any) -> BidTaskEntity:
    """供 M0 持久化阶段使用：把 ORM 行映射为实体。"""
    return BidTaskEntity(
        id=str(row.id),
        tenant_id=str(row.tenant_id),
        project_name=str(row.project_name),
        tender_no=str(row.tender_no),
        tender_entity=str(row.tender_entity),
        deadline=row.deadline,
        status=str(row.status),
        current_step=int(row.current_step),
        progress_percent=int(row.progress_percent),
        assignee_id=str(row.assignee_id),
        assignee_name=str(row.assignee_name),
        tags=list(row.tags or []),
        description=row.description,
        tender_file_id=str(row.tender_file_id) if row.tender_file_id else None,
        tender_file_name=row.tender_file_name,
        tender_mime_type=getattr(row, "tender_mime_type", None),
        tender_size_bytes=int(getattr(row, "tender_size_bytes", 0) or 0),
        tender_sha256=getattr(row, "tender_sha256", None),
        tender_scan_status=getattr(row, "tender_scan_status", None),
        tender_file_created_at=getattr(row, "tender_file_created_at", None),
        tender_preview_url=getattr(row, "tender_preview_url", None),
        tender_download_url=getattr(row, "tender_download_url", None),
        linked_evaluation_id=str(row.linked_evaluation_id) if row.linked_evaluation_id else None,
        archived_reason=row.archived_reason,
        failed_stage=getattr(row, "failed_stage", None),
        version=int(row.version),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
