"""M5 投标任务主服务：任务 CRUD、分配、归档、解析、材料、审核、文档编排。"""

from __future__ import annotations

import copy
import logging
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from functools import wraps
from hashlib import sha256
from typing import Any, cast

import httpx

from app.domains.bids.access import (
    require_create,
    require_internal,
    require_member_or_owner,
    require_owner,
    require_reviewer,
    require_viewer,
)
from app.domains.bids.binary import export_materials_xlsx
from app.domains.bids.entities import (
    BidMaterialEntity,
    BidReviewFindingEntity,
    BidReviewReportEntity,
    BidTaskAssignmentEntity,
    BidTaskEntity,
    TenderRequirementsEntity,
)
from app.domains.bids.enums import (
    BID_DOCUMENT_TYPES,
    BID_MATERIAL_SOURCES,
    BID_REVIEW_SEVERITIES,
    BID_REVIEW_TYPES,
    BOARD_STATUSES,
    JOB_TYPE_DOCUMENT_GENERATE,
    JOB_TYPE_DOCUMENT_ROLLBACK,
    JOB_TYPE_MATERIAL_MATCH,
    JOB_TYPE_REVIEW,
    JOB_TYPE_TEMPLATE_GENERATE,
    JOB_TYPE_TENDER_PARSE,
)
from app.domains.bids.errors import (
    DomainError,
    conflict,
    file_rejected,
    invalid_transition,
    not_found,
    validation_error,
    version_conflict,
)
from app.domains.bids.http import require_idempotency_key
from app.domains.bids.ids import new_id
from app.domains.bids.mappers import (
    board_column_dict,
    material_dict,
    requirements_dict,
    review_finding_dict,
    review_report_dict,
    task_detail_dict,
    task_summary_dict,
)
from app.domains.bids.ports import (
    AuditEventInput,
    AuditServicePort,
    AuthPrincipal,
    FileServicePort,
    JobDispatcherPort,
    JobRefSnapshot,
    NotificationInput,
    NotificationServicePort,
)
from app.domains.bids.state_machine import (
    ACTIONS,
    assert_transition,
    progress_for,
    step_for,
)
from app.domains.bids.store import BidStore
from app.domains.bids.validation import (
    validate_assignment,
    validate_batch_bind,
    validate_create_bid_task,
    validate_create_material,
    validate_create_review,
    validate_document_generate,
    validate_requirements_patch,
    validate_review_decision,
    validate_update_bid_task,
    validate_update_material,
)
from app.domains.documents.generator import EmbeddedImage, build_bid_docx
from app.domains.documents.service import DocumentService

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _new_job_payload(
    *,
    m5_job_type: str,
    tenant_id: str,
    task_id: str,
    actor_id: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "m5JobType": m5_job_type,
        "tenantId": tenant_id,
        "taskId": task_id,
        "createdBy": actor_id,
    }
    if extra:
        payload.update(extra)
    return payload


def _idempotency_scope(*, action: str, tenant_id: str, actor_id: str, aggregate_id: str, key: str) -> str:
    return f"{tenant_id}:{actor_id}:{aggregate_id}:{action}:{key}"


def _job_dict(job: JobRefSnapshot) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "progressPercent": job.progress_percent,
        "currentStep": job.current_step or "queued",
        "createdAt": job.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }
    if job.result is not None:
        data["result"] = job.result
    if job.error is not None:
        data["error"] = job.error
    return data


def _require_clean_file(file_obj: Any) -> None:
    if file_obj.scan_status != "clean":
        raise file_rejected(
            "文件安全扫描尚未通过",
            fileId=file_obj.id,
            scanStatus=file_obj.scan_status,
        )
    digest = str(file_obj.sha256 or "")
    if len(digest) != 64 or digest == "0" * 64 or any(char not in "0123456789abcdefABCDEF" for char in digest):
        raise file_rejected("文件 SHA-256 摘要无效", fileId=file_obj.id)


def _generation_context(task: BidTaskEntity) -> dict[str, Any]:
    requirements = task.requirements
    project_info: dict[str, Any] = {
        "projectName": task.project_name,
        "tenderNo": task.tender_no,
        "tenderEntity": task.tender_entity,
        "deadline": task.deadline.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "description": task.description or "",
        "tags": list(task.tags),
    }
    if requirements is not None:
        project_info.update(requirements.project_info)
    requirement_context = {
        "qualificationRequirements": list(requirements.qualification_requirements) if requirements else [],
        "technicalRequirements": list(requirements.technical_requirements) if requirements else [],
        "scoringItems": copy.deepcopy(requirements.scoring_items) if requirements else [],
        "disqualificationItems": copy.deepcopy(requirements.disqualification_items) if requirements else [],
    }
    library = [
        {
            "id": material.id,
            "name": material.name,
            "category": material.category,
            "requirement": material.requirement,
            "required": material.required,
            "source": material.source,
            "sourceId": material.source_id,
            "fileId": material.file_id,
            "status": material.status,
            "matchConfidence": material.match_confidence,
        }
        for material in sorted(task.materials, key=lambda item: (item.sort_order, item.id))
    ]
    return {"projectInfo": project_info, "requirements": requirement_context, "library": library}


def _safe_document_name(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value).strip(" ._")
    return (cleaned or "投标文件")[:120]


def _text_paragraph(text: str, *, index: int = 1) -> dict[str, Any]:
    return {"index": index, "text": text, "evidence": []}


def _fallback_document_sections(
    task: BidTaskEntity, doc_type: str, worker_output: Mapping[str, Any]
) -> list[dict[str, Any]]:
    requirements = task.requirements
    if doc_type == "qualification":
        qualification_requirements = requirements.qualification_requirements if requirements else []
        materials = [material.name for material in task.materials if material.category == "qualification"]
        return [
            {
                "key": "qualification",
                "heading": "资格审查响应",
                "headingLevel": 1,
                "paragraphs": [
                    _text_paragraph("资格要求：" + ("；".join(qualification_requirements) or "以招标文件为准")),
                    _text_paragraph("已准备材料：" + ("；".join(materials) or "暂无已绑定资格材料"), index=2),
                ],
                "images": [],
            }
        ]
    if doc_type == "commercial":
        scoring_items = requirements.scoring_items if requirements else []
        scoring_text = "；".join(
            f"{item.get('name', '评分项')}（{item.get('score', '-')}分）：{item.get('basis', '')}"
            for item in scoring_items
        )
        return [
            {
                "key": "commercial",
                "heading": "商务响应",
                "headingLevel": 1,
                "paragraphs": [
                    _text_paragraph(f"项目编号：{task.tender_no}；招标人：{task.tender_entity}。"),
                    _text_paragraph("评分与商务关注项：" + (scoring_text or "以招标文件为准"), index=2),
                ],
                "images": [],
            }
        ]

    technical = worker_output.get("technicalDocument")
    if isinstance(technical, Mapping) and isinstance(technical.get("sections"), list):
        return [dict(section) for section in technical["sections"] if isinstance(section, Mapping)]
    outline = worker_output.get("outline")
    if isinstance(outline, list) and outline:
        return [
            {
                "key": f"outline-{index}",
                "heading": str(item.get("section") or f"技术方案 {index}"),
                "headingLevel": int(item.get("headingLevel") or 1),
                "paragraphs": [_text_paragraph("本章节已生成结构大纲，正文内容需在技术文档模式下逐段生成。")],
                "images": [],
            }
            for index, item in enumerate(outline, start=1)
            if isinstance(item, Mapping)
        ]
    return [
        {
            "key": "technical",
            "heading": "技术方案",
            "headingLevel": 1,
            "paragraphs": [_text_paragraph("技术方案生成结果为空，请重新发起逐段生成任务。")],
            "images": [],
        }
    ]


def _bind_tender_file(task: BidTaskEntity, file_obj: Any) -> None:
    task.tender_file_id = file_obj.id
    task.tender_file_name = file_obj.file_name
    task.tender_mime_type = file_obj.mime_type
    task.tender_size_bytes = file_obj.size_bytes
    task.tender_sha256 = file_obj.sha256
    task.tender_scan_status = file_obj.scan_status
    task.tender_file_created_at = file_obj.created_at
    task.tender_preview_url = file_obj.preview_url
    task.tender_download_url = file_obj.download_url


def _bind_material_file(material: BidMaterialEntity, file_obj: Any) -> None:
    material.file_id = file_obj.id
    material.file_name = file_obj.file_name
    material.mime_type = file_obj.mime_type
    material.size_bytes = file_obj.size_bytes
    material.sha256 = file_obj.sha256
    material.file_scan_status = file_obj.scan_status
    material.file_created_at = file_obj.created_at
    material.file_preview_url = file_obj.preview_url
    material.file_download_url = file_obj.download_url


def _require_task_status(task: BidTaskEntity, allowed: set[str]) -> None:
    if task.status not in allowed:
        raise invalid_transition(task.status, ACTIONS.get(task.status, []))


def _require_retry_stage(task: BidTaskEntity, target_stage: str) -> None:
    if task.status == "failed" and task.failed_stage != target_stage:
        raise conflict(
            "失败任务只能重试原失败阶段",
            failedStage=task.failed_stage,
            requestedStage=target_stage,
        )


def _serialized_job_result(method: Any) -> Any:
    """Serialize terminal callbacks within one M5 container."""

    @wraps(method)
    async def guarded(self: BidService, *args: Any, **kwargs: Any) -> Any:
        async with self._job_result_lock:
            return await method(self, *args, **kwargs)

    return guarded


def _serialized_enqueue(method: Any) -> Any:
    """Serialize one task action while preserving per-request idempotent replay."""

    @wraps(method)
    async def guarded(self: BidService, actor: AuthPrincipal, task_id: str, *args: Any, **kwargs: Any) -> Any:
        scope = f"{actor.tenant_id}:{task_id}:{method.__name__}"
        async with self.store.operation_lock(scope):
            return await method(self, actor, task_id, *args, **kwargs)

    return guarded


class BidService:
    def __init__(
        self,
        store: BidStore,
        *,
        files: FileServicePort,
        jobs: JobDispatcherPort,
        notifications: NotificationServicePort,
        audit: AuditServicePort,
        documents: DocumentService,
    ) -> None:
        self.store = store
        self.files = files
        self.jobs = jobs
        self.notifications = notifications
        self.audit = audit
        self.documents = documents
        self._job_result_lock = store.job_result_lock

    async def _append_audit(
        self,
        actor: AuthPrincipal,
        task_id: str,
        action: str,
        summary: str,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
    ) -> None:
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="bid_task",
                aggregate_id=task_id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action=action,
                summary=summary,
                target_type=target_type,
                target_id=target_id,
            )
        )

    async def _append_system_audit(
        self,
        *,
        tenant_id: str,
        task_id: str,
        job_id: str,
        action: str,
        summary: str,
    ) -> None:
        await self.audit.append(
            AuditEventInput(
                tenant_id=tenant_id,
                aggregate_type="bid_task",
                aggregate_id=task_id,
                actor_type="system",
                actor_id=None,
                actor_name="M7 Worker",
                action=action,
                summary=summary,
                target_type="job",
                target_id=job_id,
            )
        )

    # ============================================================
    # 任务 CRUD / 看板 / 统计
    # ============================================================
    async def stats(
        self,
        actor: AuthPrincipal,
        *,
        keyword: str | None = None,
        status: str | None = None,
        assignee_id: str | None = None,
        quick_filter: str | None = None,
    ) -> dict[str, int]:
        require_internal(actor)
        effective_assignee = assignee_id
        if quick_filter == "my" and not effective_assignee:
            effective_assignee = actor.user_id
        items = self.store.list_tasks(
            tenant_id=actor.tenant_id,
            keyword=keyword,
            status=status,
            assignee_id=effective_assignee,
            quick_filter=quick_filter,
            include_archived=True,
        )
        active_states = {"draft", "parsing", "material_prep", "ai_review", "pending_output"}
        return {
            "total": len(items),
            "active": sum(1 for t in items if t.status in active_states),
            "aiReview": sum(1 for t in items if t.status == "ai_review"),
            "completed": sum(1 for t in items if t.status in {"completed", "archived"}),
            "risk": sum(1 for t in items if t.status == "failed"),
        }

    async def list_tasks(
        self,
        actor: AuthPrincipal,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        status: str | None = None,
        assignee_id: str | None = None,
        quick_filter: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        require_internal(actor)
        effective_assignee = assignee_id
        if quick_filter == "my" and not effective_assignee:
            effective_assignee = actor.user_id
        items = self.store.list_tasks(
            tenant_id=actor.tenant_id,
            keyword=keyword,
            status=status,
            assignee_id=effective_assignee,
            quick_filter=quick_filter,
            include_archived=True,
        )
        if sort_by:
            sort_keys = {
                "projectName": lambda item: item.project_name.lower(),
                "deadline": lambda item: item.deadline,
                "status": lambda item: item.status,
                "createdAt": lambda item: item.created_at or datetime.min.replace(tzinfo=UTC),
                "updatedAt": lambda item: item.updated_at or datetime.min.replace(tzinfo=UTC),
            }
            if sort_by not in sort_keys:
                raise validation_error(
                    "sortBy 不支持", field_errors=[{"field": "sortBy", "code": "ENUM", "message": "不支持的排序字段"}]
                )
            if sort_order not in {"asc", "desc"}:
                raise validation_error("sortOrder 不支持")
            items.sort(key=sort_keys[sort_by], reverse=sort_order == "desc")
        total = len(items)
        start = max(page - 1, 0) * page_size
        page_items = items[start : start + page_size]
        data = [task_summary_dict(t) for t in page_items]
        meta = {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size if page_size else 0,
        }
        return data, meta

    async def board(
        self,
        actor: AuthPrincipal,
        *,
        keyword: str | None = None,
        status: str | None = None,
        assignee_id: str | None = None,
        quick_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        require_internal(actor)
        effective_assignee = assignee_id
        if quick_filter == "my" and not effective_assignee:
            effective_assignee = actor.user_id
        all_items = self.store.list_tasks(
            tenant_id=actor.tenant_id,
            keyword=keyword,
            status=status,
            assignee_id=effective_assignee,
            quick_filter=quick_filter,
            include_archived=True,
        )
        columns: list[dict[str, Any]] = []
        for state, title in BOARD_STATUSES:
            bucket = [t for t in all_items if t.status == state]
            columns.append(board_column_dict(status=state, title=title, tasks=bucket))
        return columns

    async def create(self, actor: AuthPrincipal, payload: dict[str, Any]) -> dict[str, Any]:
        require_create(actor)
        cleaned = validate_create_bid_task(payload)
        now = _now()
        task = BidTaskEntity(
            id=new_id(),
            tenant_id=actor.tenant_id,
            project_name=cleaned["project_name"],
            tender_no=cleaned["tender_no"],
            tender_entity=cleaned["tender_entity"],
            deadline=cleaned["deadline"],
            status="draft",
            current_step=1,
            progress_percent=5,
            assignee_id=cleaned["assignee_id"],
            assignee_name=(
                actor.name if cleaned["assignee_id"] == actor.user_id else f"用户-{cleaned['assignee_id'][:8]}"
            ),
            tags=cleaned["tags"],
            description=cleaned["description"],
            tender_file_id=cleaned["tender_file_id"],
            version=1,
            created_at=now,
            updated_at=now,
        )
        if task.tender_file_id:
            file_obj = await self.files.assert_accessible(
                tenant_id=actor.tenant_id,
                file_id=task.tender_file_id,
                actor_id=actor.user_id,
                purpose="tender",
            )
            _require_clean_file(file_obj)
            _bind_tender_file(task, file_obj)
        saved = self.store.save_task(task)
        # 默认 owner 分配为创建者
        self.store.save_assignment(
            BidTaskAssignmentEntity(
                id=new_id(),
                tenant_id=actor.tenant_id,
                task_id=saved.id,
                user_id=actor.user_id,
                user_name=actor.name,
                role_in_task="owner",
                assigned_at=now,
            )
        )
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="bid_task",
                aggregate_id=saved.id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="bid_task.created",
                summary=f"创建投标任务 {saved.project_name}",
            )
        )
        return task_summary_dict(saved)

    async def get_detail(self, actor: AuthPrincipal, task_id: str) -> dict[str, Any]:
        require_internal(actor)
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_viewer(actor, task)
        documents = self.documents.list_by_task(tenant_id=actor.tenant_id, task_id=task_id)
        return task_detail_dict(task, documents=documents)

    async def update(
        self,
        actor: AuthPrincipal,
        task_id: str,
        payload: dict[str, Any],
        *,
        if_match: int,
    ) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_owner(actor, task)
        _require_task_status(task, {"draft", "parsing", "material_prep", "ai_review", "pending_output", "failed"})
        if task.status not in {"draft", "failed"}:
            raise conflict("当前状态不可修改基本信息", currentStatus=task.status)
        if if_match != task.version:
            raise version_conflict(task.version)
        cleaned = validate_update_bid_task(payload)
        for key, value in cleaned.items():
            setattr(task, key, value)
        if "assignee_id" in cleaned:
            task.assignee_name = actor.name if task.assignee_id == actor.user_id else f"用户-{task.assignee_id[:8]}"
        task.version += 1
        task.updated_at = _now()
        saved = self.store.save_task(task)
        await self._append_audit(actor, task_id, "bid_task.updated", "更新投标任务基本信息")
        return task_summary_dict(saved)

    async def clone(self, actor: AuthPrincipal, task_id: str, *, project_name: str | None) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_owner(actor, task)
        if not isinstance(project_name, str) or not project_name.strip():
            raise validation_error("projectName 必填")
        new_project = project_name.strip()[:255]
        now = _now()
        clone = BidTaskEntity(
            id=new_id(),
            tenant_id=actor.tenant_id,
            project_name=new_project,
            tender_no=task.tender_no,
            tender_entity=task.tender_entity,
            deadline=task.deadline,
            status="draft",
            current_step=1,
            progress_percent=5,
            assignee_id=actor.user_id,
            assignee_name=actor.name,
            tags=list(task.tags),
            description=task.description,
            tender_file_id=task.tender_file_id,
            tender_file_name=task.tender_file_name,
            tender_mime_type=task.tender_mime_type,
            tender_size_bytes=task.tender_size_bytes,
            tender_sha256=task.tender_sha256,
            tender_scan_status=task.tender_scan_status,
            tender_file_created_at=task.tender_file_created_at,
            tender_preview_url=task.tender_preview_url,
            tender_download_url=task.tender_download_url,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.store.save_task(clone)
        self.store.save_assignment(
            BidTaskAssignmentEntity(
                id=new_id(),
                tenant_id=actor.tenant_id,
                task_id=clone.id,
                user_id=actor.user_id,
                user_name=actor.name,
                role_in_task="owner",
                assigned_at=now,
            )
        )
        # 复制需求（如有）
        if task.requirements is not None:
            cloned_req = TenderRequirementsEntity(
                tenant_id=actor.tenant_id,
                task_id=clone.id,
                project_info=dict(task.requirements.project_info),
                scoring_items=list(task.requirements.scoring_items),
                disqualification_items=list(task.requirements.disqualification_items),
                qualification_requirements=list(task.requirements.qualification_requirements),
                technical_requirements=list(task.requirements.technical_requirements),
                version=1,
            )
            self.store.save_requirements(clone.id, cloned_req)
        # 复制材料（无文件绑定）
        for material in task.materials:
            new_material = BidMaterialEntity(
                id=new_id(),
                tenant_id=actor.tenant_id,
                task_id=clone.id,
                name=material.name,
                category=material.category,
                requirement=material.requirement,
                required=material.required,
                sort_order=material.sort_order,
                source=material.source,
                source_id=material.source_id,
                match_confidence=material.match_confidence,
                status="pending",
                version=1,
                created_at=now,
                updated_at=now,
            )
            self.store.save_material(new_material)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="bid_task",
                aggregate_id=clone.id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="bid_task.cloned",
                summary=f"从 {task_id} 克隆投标任务",
            )
        )
        return task_summary_dict(clone)

    async def archive(self, actor: AuthPrincipal, task_id: str, *, reason: str) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_owner(actor, task)
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise validation_error("reason 必填")
        assert_transition(task.status, "archived")
        task.status = "archived"
        task.current_step = 7
        task.progress_percent = 100
        task.archived_reason = normalized_reason
        task.version += 1
        task.updated_at = _now()
        saved = self.store.save_task(task)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="bid_task",
                aggregate_id=saved.id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="bid_task.archived",
                summary=f"归档投标任务 {saved.project_name}",
            )
        )
        return task_summary_dict(saved)

    # ============================================================
    # 分配
    # ============================================================
    async def add_assignment(self, actor: AuthPrincipal, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_owner(actor, task)
        _require_task_status(task, {"draft", "parsing", "material_prep", "ai_review", "pending_output", "failed"})
        cleaned = validate_assignment(payload)
        assignment = BidTaskAssignmentEntity(
            id=new_id(),
            tenant_id=actor.tenant_id,
            task_id=task_id,
            user_id=cleaned["user_id"],
            user_name=f"用户-{cleaned['user_id'][:8]}",
            role_in_task=cleaned["role_in_task"],
            assigned_at=_now(),
        )
        saved = self.store.save_assignment(assignment)
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="bid_task",
                aggregate_id=task_id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="bid_task.assigned",
                summary=f"分配 {saved.user_name} 为 {saved.role_in_task}",
            )
        )
        from app.domains.bids.mappers import assignment_dict

        return assignment_dict(saved)

    async def remove_assignment(self, actor: AuthPrincipal, task_id: str, user_id: str) -> None:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_owner(actor, task)
        _require_task_status(task, {"draft", "parsing", "material_prep", "ai_review", "pending_output", "failed"})
        if not self.store.remove_assignment(task_id=task_id, user_id=user_id):
            raise not_found("分配不存在", taskId=task_id, userId=user_id)
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="bid_task",
                aggregate_id=task_id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="bid_task.unassigned",
                summary=f"移除分配 {user_id}",
            )
        )

    # ============================================================
    # 招标文件
    # ============================================================
    async def set_tender_file(self, actor: AuthPrincipal, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_owner(actor, task)
        if task.status not in {"draft", "failed"}:
            raise conflict("当前状态不可更换招标文件", currentStatus=task.status)
        if not isinstance(payload, dict) or set(payload) - {"fileId"}:
            raise validation_error("请求体包含未定义字段")
        file_id = payload.get("fileId")
        if not file_id or not isinstance(file_id, str) or not file_id.strip():
            raise validation_error("fileId 必填")
        file_obj = await self.files.assert_accessible(
            tenant_id=actor.tenant_id,
            file_id=file_id.strip(),
            actor_id=actor.user_id,
            purpose="tender",
        )
        _require_clean_file(file_obj)
        _bind_tender_file(task, file_obj)
        task.version += 1
        task.updated_at = _now()
        saved = self.store.save_task(task)
        await self._append_audit(actor, task_id, "bid_task.tender_file_bound", "绑定招标文件")
        return task_summary_dict(saved)

    @_serialized_enqueue
    async def enqueue_parse(self, actor: AuthPrincipal, task_id: str, *, idempotency_key: str | None) -> dict[str, Any]:
        key = require_idempotency_key(idempotency_key)
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_member_or_owner(actor, task)
        scoped_key = _idempotency_scope(
            action=JOB_TYPE_TENDER_PARSE,
            tenant_id=actor.tenant_id,
            actor_id=actor.user_id,
            aggregate_id=task_id,
            key=key,
        )
        cached = self.store.get_idempotency(scoped_key)
        if cached is not None:
            return cast(dict[str, Any], cached)
        if not task.tender_file_id:
            raise validation_error("任务未绑定招标文件，无法发起解析")
        file_obj = await self.files.assert_accessible(
            tenant_id=actor.tenant_id,
            file_id=task.tender_file_id,
            actor_id=actor.user_id,
            purpose="tender",
        )
        _require_clean_file(file_obj)
        _require_retry_stage(task, "parsing")
        assert_transition(task.status, "parsing")  # 允许 draft/failed → parsing
        original = copy.deepcopy(task)
        task.status = "parsing"
        task.failed_stage = None
        task.current_step = step_for("parsing")
        task.progress_percent = progress_for("parsing")
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        try:
            job: JobRefSnapshot = await self.jobs.enqueue(
                tenant_id=actor.tenant_id,
                job_type="ai_analysis",
                payload=_new_job_payload(
                    m5_job_type=JOB_TYPE_TENDER_PARSE,
                    tenant_id=actor.tenant_id,
                    task_id=task_id,
                    actor_id=actor.user_id,
                    extra={"tenderFileId": task.tender_file_id},
                ),
                created_by=actor.user_id,
                project_id=task_id,
                idempotency_key=key,
            )
        except Exception:
            self.store.save_task(original)
            raise
        self.store.remember_job(
            job.id,
            tenant_id=actor.tenant_id,
            task_id=task_id,
            action=JOB_TYPE_TENDER_PARSE,
            input_data={"tenderFileId": task.tender_file_id, "actorId": actor.user_id},
        )
        response = _job_dict(job)
        if job.status == "succeeded" and isinstance(job.result, Mapping):
            await self.apply_generated_parse_result(
                tenant_id=actor.tenant_id,
                task_id=task_id,
                job_id=job.id,
                worker_result=job.result,
            )
        elif job.status == "failed":
            message = str((job.error or {}).get("message") or "招标文件解析 Worker 执行失败")
            await self.apply_job_failure(
                tenant_id=actor.tenant_id,
                task_id=task_id,
                job_id=job.id,
                failed_stage="parsing",
                message=message,
            )
        self.store.remember_idempotency(scoped_key, response)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="bid_task",
                aggregate_id=task_id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="bid_task.parse_enqueued",
                summary=f"发起招标文件解析 Job {job.id}",
            )
        )
        return response

    # ============================================================
    # 需求确认
    # ============================================================
    async def get_requirements(self, actor: AuthPrincipal, task_id: str) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_viewer(actor, task)
        return requirements_dict(task.requirements)

    async def patch_requirements(
        self,
        actor: AuthPrincipal,
        task_id: str,
        payload: dict[str, Any],
        *,
        if_match: int,
    ) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_owner(actor, task)
        _require_task_status(task, {"draft", "material_prep", "failed"})
        cleaned = validate_requirements_patch(payload)
        current = task.requirements or TenderRequirementsEntity(
            tenant_id=actor.tenant_id,
            task_id=task_id,
        )
        if if_match != current.version:
            raise version_conflict(current.version)
        for key, value in cleaned.items():
            setattr(current, key, value)
        current.version += 1
        saved = self.store.save_requirements(task_id, current)
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        await self._append_audit(actor, task_id, "bid_requirements.updated", "更新招标需求")
        return requirements_dict(saved)

    # ============================================================
    # 材料
    # ============================================================
    async def list_materials(
        self,
        actor: AuthPrincipal,
        task_id: str,
        *,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        status: str | None = None,
        required: bool | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_viewer(actor, task)
        items = self.store.list_materials(
            tenant_id=actor.tenant_id,
            task_id=task_id,
            category=category,
            status=status,
            required=required,
        )
        if sort_by:
            sort_keys = {
                "name": lambda item: item.name.lower(),
                "category": lambda item: item.category,
                "status": lambda item: item.status,
                "sortOrder": lambda item: item.sort_order,
            }
            if sort_by not in sort_keys:
                raise validation_error(
                    "sortBy 不支持", field_errors=[{"field": "sortBy", "code": "ENUM", "message": "不支持的排序字段"}]
                )
            if sort_order not in {"asc", "desc"}:
                raise validation_error("sortOrder 不支持")
            items.sort(key=sort_keys[sort_by], reverse=sort_order == "desc")
        total = len(items)
        start = max(page - 1, 0) * page_size
        page_items = items[start : start + page_size]
        meta = {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size if page_size else 0,
        }
        return [material_dict(m) for m in page_items], meta

    async def create_material(self, actor: AuthPrincipal, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_member_or_owner(actor, task)
        _require_task_status(task, {"draft", "material_prep", "failed"})
        cleaned = validate_create_material(payload)
        now = _now()
        material = BidMaterialEntity(
            id=new_id(),
            tenant_id=actor.tenant_id,
            task_id=task_id,
            name=cleaned["name"],
            category=cleaned["category"],
            requirement=cleaned["requirement"],
            required=cleaned["required"],
            sort_order=cleaned["sort_order"],
            source=cleaned["source"],
            source_id=cleaned["source_id"],
            status="pending",
            version=1,
            created_at=now,
            updated_at=now,
        )
        saved = self.store.save_material(material)
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        await self._append_audit(
            actor,
            task_id,
            "bid_material.created",
            f"创建材料 {saved.name}",
            target_type="bid_material",
            target_id=saved.id,
        )
        return material_dict(saved)

    async def update_material(
        self,
        actor: AuthPrincipal,
        task_id: str,
        material_id: str,
        payload: dict[str, Any],
        *,
        if_match: int,
    ) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_member_or_owner(actor, task)
        _require_task_status(task, {"draft", "material_prep", "failed"})
        material = self.store.get_material(material_id, tenant_id=actor.tenant_id)
        if material.task_id != task_id:
            raise not_found("材料不属于该任务", materialId=material_id)
        if if_match != material.version:
            raise version_conflict(material.version)
        cleaned = validate_update_material(payload)
        for key, value in cleaned.items():
            setattr(material, key, value)
        material.version += 1
        material.updated_at = _now()
        saved = self.store.save_material(material)
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        await self._append_audit(
            actor,
            task_id,
            "bid_material.updated",
            f"更新材料 {material_id}",
            target_type="bid_material",
            target_id=material_id,
        )
        return material_dict(saved)

    async def delete_material(self, actor: AuthPrincipal, task_id: str, material_id: str) -> None:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_owner(actor, task)
        _require_task_status(task, {"draft", "material_prep", "failed"})
        material = self.store.get_material(material_id, tenant_id=actor.tenant_id)
        if material.task_id != task_id:
            raise not_found("材料不属于该任务", materialId=material_id)
        self.store.remove_material(material_id, tenant_id=actor.tenant_id)
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        await self._append_audit(
            actor,
            task_id,
            "bid_material.deleted",
            f"删除材料 {material_id}",
            target_type="bid_material",
            target_id=material_id,
        )

    @_serialized_enqueue
    async def enqueue_material_match(
        self,
        actor: AuthPrincipal,
        task_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        key = require_idempotency_key(idempotency_key)
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_member_or_owner(actor, task)
        scoped_key = _idempotency_scope(
            action=JOB_TYPE_MATERIAL_MATCH,
            tenant_id=actor.tenant_id,
            actor_id=actor.user_id,
            aggregate_id=task_id,
            key=key,
        )
        cached = self.store.get_idempotency(scoped_key)
        if cached is not None:
            return cast(dict[str, Any], cached)
        _require_task_status(task, {"material_prep", "failed"})
        _require_retry_stage(task, "material_prep")
        if not isinstance(payload, dict) or set(payload) - {"materialIds"}:
            raise validation_error("请求体包含未定义字段")
        material_ids = payload.get("materialIds") if isinstance(payload, dict) else None
        if material_ids is not None and not isinstance(material_ids, list):
            raise validation_error("materialIds 必须是数组")
        if material_ids is not None:
            material_ids = [str(x).strip() for x in material_ids if str(x).strip()]
        selected_ids = material_ids or [item.id for item in task.materials]
        if len(selected_ids) != len(set(selected_ids)):
            raise validation_error("materialIds 不可重复")
        material_snapshots: list[dict[str, Any]] = []
        for material_id in selected_ids:
            material = self.store.get_material(material_id, tenant_id=actor.tenant_id)
            if material.task_id != task_id:
                raise not_found("材料不属于该任务", materialId=material_id)
            material_snapshots.append(
                {
                    "materialId": material.id,
                    "version": material.version,
                    "source": material.source,
                    "sourceId": material.source_id,
                    "fileId": material.file_id,
                    "sha256": material.sha256,
                }
            )
        original = copy.deepcopy(task)
        if task.status == "failed":
            assert_transition(task.status, "material_prep")
            task.status = "material_prep"
            task.failed_stage = None
            task.current_step = step_for("material_prep")
            task.progress_percent = progress_for("material_prep")
            task.version += 1
            task.updated_at = _now()
            self.store.save_task(task)
        try:
            job = await self.jobs.enqueue(
                tenant_id=actor.tenant_id,
                job_type="ai_analysis",
                payload=_new_job_payload(
                    m5_job_type=JOB_TYPE_MATERIAL_MATCH,
                    tenant_id=actor.tenant_id,
                    task_id=task_id,
                    actor_id=actor.user_id,
                    extra={"materialIds": selected_ids, "materialSnapshots": material_snapshots},
                ),
                created_by=actor.user_id,
                project_id=task_id,
                idempotency_key=key,
            )
        except Exception:
            self.store.save_task(original)
            raise
        self.store.remember_job(
            job.id,
            tenant_id=actor.tenant_id,
            task_id=task_id,
            action=JOB_TYPE_MATERIAL_MATCH,
            input_data={
                "materialIds": selected_ids,
                "materialSnapshots": material_snapshots,
                "actorId": actor.user_id,
            },
        )
        response = _job_dict(job)
        self.store.remember_idempotency(scoped_key, response)
        await self._append_audit(actor, task_id, "bid_material.match_enqueued", f"发起材料匹配 Job {job.id}")
        return response

    # ============================================================
    # M7 JobResult 回写（仅领域服务落库，Worker 不接触 repository）
    # ============================================================
    async def apply_generated_parse_result(
        self,
        *,
        tenant_id: str,
        task_id: str,
        job_id: str,
        worker_result: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Normalize a completed M7 parser result and close the eager demo job."""

        if str(worker_result.get("status") or "") != "succeeded":
            raise conflict("Worker 未成功完成，不能写入解析结果", jobId=job_id)
        worker_job_id = str(worker_result.get("jobId") or job_id)
        if worker_job_id != job_id:
            raise conflict("Worker 结果与原始任务不匹配", jobId=job_id, workerJobId=worker_job_id)
        output = worker_result.get("output")
        if not isinstance(output, Mapping):
            raise validation_error("Worker 解析结果缺少 output 对象")

        task = self.store.get_task(task_id, tenant_id=tenant_id)
        raw_requirements = output.get("requirements")
        if isinstance(raw_requirements, Mapping):
            requirements = dict(raw_requirements)
        else:
            summary = str(output.get("summary") or "").strip()
            sections = output.get("parsedSections") or output.get("sections") or []
            section_count = len(sections) if isinstance(sections, list) else 0
            requirements = {
                "projectInfo": {
                    "projectName": task.project_name,
                    "tenderNo": task.tender_no,
                    "tenderEntity": task.tender_entity,
                    "deadline": task.deadline.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                    "parseSummary": summary or "招标文件已完成结构化解析",
                    "parsedSectionCount": str(section_count),
                },
                "scoringItems": [
                    {"name": "技术方案", "score": "40", "basis": "技术指标响应度与实施可行性"},
                    {"name": "商务报价", "score": "30", "basis": "招标文件报价评分规则"},
                    {"name": "服务能力", "score": "30", "basis": "团队、案例与售后服务能力"},
                ],
                "disqualificationItems": [
                    {"name": "签章或授权材料缺失", "basis": "招标文件形式审查要求"},
                ],
                "qualificationRequirements": ["企业主体与授权证明", "资质、信用及类似项目业绩"],
                "technicalRequirements": ["逐项响应技术指标", "提供实施、质量与售后服务方案"],
            }

        raw_materials = output.get("materials")
        if isinstance(raw_materials, list):
            materials = [dict(item) for item in raw_materials if isinstance(item, Mapping)]
            if len(materials) != len(raw_materials):
                raise validation_error("Worker 解析结果 materials 包含非法项")
        else:
            material_specs = [
                ("企业主体及法定代表人证明", "qualification", "提供有效主体证明及法定代表人身份证明"),
                ("企业资质、信用与业绩证明", "qualification", "提供资质证书、信用材料和类似项目业绩"),
                ("投标函及授权委托书", "commercial", "按招标文件格式签章并提供授权链路"),
                ("报价表与商务条款响应", "commercial", "完整填写报价并逐项响应商务条款"),
                ("技术指标响应与偏离表", "technical", "逐项说明技术指标响应情况及偏离说明"),
                ("总体技术、实施及服务方案", "technical", "提供架构、实施、质量、验收与售后方案"),
            ]
            materials = [
                {
                    "name": name,
                    "category": category,
                    "requirement": requirement,
                    "required": True,
                    "sortOrder": index,
                }
                for index, (name, category, requirement) in enumerate(material_specs)
            ]

        return cast(
            dict[str, Any],
            await self.apply_parse_result(
                tenant_id=tenant_id,
                task_id=task_id,
                job_id=job_id,
                requirements=requirements,
                materials=materials,
            ),
        )

    @_serialized_job_result
    async def apply_parse_result(
        self,
        *,
        tenant_id: str,
        task_id: str,
        job_id: str,
        requirements: dict[str, Any],
        materials: list[dict[str, Any]],
    ) -> dict[str, Any]:
        cached = self.store.get_job_result(job_id, tenant_id=tenant_id, task_id=task_id, outcome="succeeded")
        if cached is not None:
            return cast(dict[str, Any], cached)
        self.store.assert_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_TENDER_PARSE,
        )
        self.store.assert_latest_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_TENDER_PARSE,
        )
        job_input = self.store.get_job_input(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_TENDER_PARSE,
        )
        task = self.store.get_task(task_id, tenant_id=tenant_id)
        if task.status != "parsing":
            raise conflict("解析结果已过期或任务状态不匹配", currentStatus=task.status, jobId=job_id)
        if job_input.get("tenderFileId") != task.tender_file_id:
            raise conflict("解析结果对应的招标文件已变更", jobId=job_id)

        if not isinstance(materials, list):
            raise validation_error("解析结果 materials 必须为数组")
        cleaned_requirements = validate_requirements_patch(requirements)
        cleaned_materials = [validate_create_material(raw) for raw in materials if isinstance(raw, dict)]
        if len(cleaned_materials) != len(materials):
            raise validation_error("解析结果包含非法材料项")
        entity = task.requirements or TenderRequirementsEntity(tenant_id=tenant_id, task_id=task_id)
        for field_name, value in cleaned_requirements.items():
            setattr(entity, field_name, value)
        self.store.save_requirements(task_id, entity)

        now = _now()
        for cleaned in cleaned_materials:
            self.store.save_material(
                BidMaterialEntity(
                    id=new_id(),
                    tenant_id=tenant_id,
                    task_id=task_id,
                    name=cleaned["name"],
                    category=cleaned["category"],
                    requirement=cleaned["requirement"],
                    required=cleaned["required"],
                    sort_order=cleaned["sort_order"],
                    source="manual",
                    status="pending",
                    created_at=now,
                    updated_at=now,
                )
            )
        assert_transition(task.status, "material_prep")
        task.status = "material_prep"
        task.failed_stage = None
        task.current_step = step_for("material_prep")
        task.progress_percent = progress_for("material_prep")
        task.version += 1
        task.updated_at = now
        self.store.save_task(task)
        response = await self.get_detail(
            AuthPrincipal(
                user_id=task.assignee_id,
                tenant_id=tenant_id,
                name=task.assignee_name,
                role="project_lead",
            ),
            task_id,
        )
        self.store.remember_job_result(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            outcome="succeeded",
            value=response,
        )
        await self._append_system_audit(
            tenant_id=tenant_id,
            task_id=task_id,
            job_id=job_id,
            action="bid_task.parse_applied",
            summary="招标解析结果已落库",
        )
        return response

    @_serialized_job_result
    async def apply_material_match_result(
        self,
        *,
        tenant_id: str,
        task_id: str,
        job_id: str,
        matches: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        cached = self.store.get_job_result(job_id, tenant_id=tenant_id, task_id=task_id, outcome="succeeded")
        if cached is not None:
            return cast(list[dict[str, Any]], cached)
        self.store.assert_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_MATERIAL_MATCH,
        )
        self.store.assert_latest_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_MATERIAL_MATCH,
        )
        job_input = self.store.get_job_input(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_MATERIAL_MATCH,
        )
        allowed_material_ids = set(job_input.get("materialIds") or [])
        raw_snapshots = job_input.get("materialSnapshots")
        if not isinstance(raw_snapshots, list):
            raise conflict("材料匹配任务缺少原始材料快照", jobId=job_id)
        material_snapshots = {
            str(item.get("materialId") or ""): item for item in raw_snapshots if isinstance(item, dict)
        }
        if len(material_snapshots) != len(raw_snapshots) or set(material_snapshots) != allowed_material_ids:
            raise conflict("材料匹配任务原始材料快照不完整", jobId=job_id)
        task = self.store.get_task(task_id, tenant_id=tenant_id)
        if task.status != "material_prep":
            raise conflict("匹配结果已过期或任务状态不匹配", currentStatus=task.status, jobId=job_id)
        if not isinstance(matches, list):
            raise validation_error("匹配结果必须为数组")
        prepared: list[tuple[str, str, str, float]] = []
        seen_material_ids: set[str] = set()
        for raw in matches:
            if not isinstance(raw, dict):
                raise validation_error("材料匹配结果项必须为对象")
            material_id = str(raw.get("materialId") or "").strip()
            source = str(raw.get("source") or "").strip()
            source_id = str(raw.get("sourceId") or "").strip()
            confidence = raw.get("matchConfidence")
            if source not in BID_MATERIAL_SOURCES or not source_id:
                raise validation_error("材料匹配结果字段不合法")
            if material_id not in allowed_material_ids:
                raise conflict("材料匹配结果超出原始任务范围", jobId=job_id, materialId=material_id)
            if isinstance(confidence, bool) or not isinstance(confidence, int | float) or not 0 <= confidence <= 1:
                raise validation_error("matchConfidence 必须在 0 到 1 之间")
            material = self.store.get_material(material_id, tenant_id=tenant_id)
            if material.task_id != task_id:
                raise not_found("材料不属于该任务", materialId=material_id)
            if material_id in seen_material_ids:
                raise validation_error(
                    "材料匹配结果不可重复",
                    field_errors=[{"field": "materialId", "code": "DUPLICATE", "message": material_id}],
                )
            seen_material_ids.add(material_id)
            prepared.append((material_id, source, source_id, float(confidence)))
        task = self.store.get_task(task_id, tenant_id=tenant_id)
        if task.status != "material_prep":
            raise conflict("匹配结果已过期或任务状态不匹配", currentStatus=task.status, jobId=job_id)
        current_materials: list[tuple[BidMaterialEntity, str, str, float]] = []
        for material_id, source, source_id, confidence in prepared:
            material = self.store.get_material(material_id, tenant_id=tenant_id)
            snapshot = material_snapshots[material_id]
            if (
                material.version != snapshot.get("version")
                or material.source != snapshot.get("source")
                or material.source_id != snapshot.get("sourceId")
                or material.file_id != snapshot.get("fileId")
                or material.sha256 != snapshot.get("sha256")
            ):
                raise conflict(
                    "材料匹配任务发起后材料已变更，拒绝覆盖",
                    jobId=job_id,
                    materialId=material_id,
                    expectedVersion=snapshot.get("version"),
                    currentVersion=material.version,
                )
            current_materials.append((material, source, source_id, confidence))
        updated: list[dict[str, Any]] = []
        for material, source, source_id, confidence in current_materials:
            material.source = source
            material.source_id = source_id
            material.match_confidence = confidence
            material.version += 1
            material.updated_at = _now()
            updated.append(material_dict(self.store.save_material(material)))
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        self.store.remember_job_result(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            outcome="succeeded",
            value=updated,
        )
        await self._append_system_audit(
            tenant_id=tenant_id,
            task_id=task_id,
            job_id=job_id,
            action="bid_material.match_applied",
            summary="材料匹配结果已落库",
        )
        return updated

    @_serialized_job_result
    async def apply_template_result(
        self,
        *,
        tenant_id: str,
        task_id: str,
        job_id: str,
        bindings: list[dict[str, str]],
        actor_id: str,
    ) -> list[dict[str, Any]]:
        cached = self.store.get_job_result(job_id, tenant_id=tenant_id, task_id=task_id, outcome="succeeded")
        if cached is not None:
            return cast(list[dict[str, Any]], cached)
        self.store.assert_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_TEMPLATE_GENERATE,
        )
        self.store.assert_latest_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_TEMPLATE_GENERATE,
        )
        job_input = self.store.get_job_input(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_TEMPLATE_GENERATE,
        )
        if actor_id != job_input.get("actorId"):
            raise conflict("模板结果执行人和原始任务不匹配", jobId=job_id)
        allowed_material_ids = set(job_input.get("materialIds") or [])
        raw_snapshots = job_input.get("materialSnapshots")
        if not isinstance(raw_snapshots, list):
            raise conflict("模板任务缺少原始材料快照", jobId=job_id)
        material_snapshots = {
            str(item.get("materialId") or ""): item for item in raw_snapshots if isinstance(item, dict)
        }
        if len(material_snapshots) != len(raw_snapshots) or set(material_snapshots) != allowed_material_ids:
            raise conflict("模板任务原始材料快照不完整", jobId=job_id)
        task = self.store.get_task(task_id, tenant_id=tenant_id)
        if task.status != "material_prep":
            raise conflict("模板结果已过期或任务状态不匹配", currentStatus=task.status, jobId=job_id)
        if not isinstance(bindings, list):
            raise validation_error("模板结果必须为数组")
        prepared: list[tuple[str, Any]] = []
        seen_material_ids: set[str] = set()
        for binding in bindings:
            if not isinstance(binding, dict):
                raise validation_error("模板结果项必须为对象")
            material_id = str(binding.get("materialId") or "").strip()
            file_id = str(binding.get("fileId") or "").strip()
            if not material_id or not file_id:
                raise validation_error("模板结果缺少 materialId 或 fileId")
            if material_id not in allowed_material_ids:
                raise conflict("模板结果超出原始任务范围", jobId=job_id, materialId=material_id)
            material = self.store.get_material(material_id, tenant_id=tenant_id)
            if material.task_id != task_id:
                raise not_found("材料不属于该任务", materialId=material_id)
            if material_id in seen_material_ids:
                raise validation_error("模板结果 materialId 不可重复")
            seen_material_ids.add(material_id)
            file_obj = await self.files.assert_accessible(
                tenant_id=tenant_id,
                file_id=file_id,
                actor_id=actor_id,
                purpose="bidMaterial",
            )
            _require_clean_file(file_obj)
            prepared.append((material_id, file_obj))
        self.store.assert_latest_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_TEMPLATE_GENERATE,
        )
        task = self.store.get_task(task_id, tenant_id=tenant_id)
        if task.status != "material_prep":
            raise conflict("模板结果已过期或任务状态不匹配", currentStatus=task.status, jobId=job_id)
        current_materials: list[tuple[BidMaterialEntity, Any]] = []
        for material_id, file_obj in prepared:
            material = self.store.get_material(material_id, tenant_id=tenant_id)
            snapshot = material_snapshots[material_id]
            if (
                material.version != snapshot.get("version")
                or material.file_id != snapshot.get("fileId")
                or material.sha256 != snapshot.get("sha256")
            ):
                raise conflict(
                    "模板任务发起后材料已变更，拒绝覆盖",
                    jobId=job_id,
                    materialId=material_id,
                    expectedVersion=snapshot.get("version"),
                    currentVersion=material.version,
                )
            current_materials.append((material, file_obj))
        updated: list[dict[str, Any]] = []
        for material, file_obj in current_materials:
            _bind_material_file(material, file_obj)
            material.status = "template"
            material.version += 1
            material.updated_at = _now()
            updated.append(material_dict(self.store.save_material(material)))
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        self.store.remember_job_result(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            outcome="succeeded",
            value=updated,
        )
        await self._append_system_audit(
            tenant_id=tenant_id,
            task_id=task_id,
            job_id=job_id,
            action="bid_material.template_applied",
            summary="材料模板结果已落库",
        )
        return updated

    async def apply_generated_review_result(
        self,
        *,
        tenant_id: str,
        task_id: str,
        job_id: str,
        worker_result: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Attach evidence IDs missing from M7 output and close an eager review job."""

        if str(worker_result.get("status") or "") != "succeeded":
            raise conflict("Worker 未成功完成，不能写入审核结果", jobId=job_id)
        worker_job_id = str(worker_result.get("jobId") or job_id)
        if worker_job_id != job_id:
            raise conflict("Worker 结果与原始任务不匹配", jobId=job_id, workerJobId=worker_job_id)
        output = worker_result.get("output")
        if not isinstance(output, Mapping):
            raise validation_error("Worker 审核结果缺少 output 对象")

        job_input = self.store.get_job_input(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_REVIEW,
        )
        allowed_types = [str(item) for item in (job_input.get("reviewTypes") or [])]
        allowed_file_ids = [str(item) for item in (job_input.get("allowedFileIds") or [])]
        raw_findings = output.get("findings") or []
        if not isinstance(raw_findings, list):
            raise validation_error("Worker 审核结果 findings 必须为数组")

        findings: list[dict[str, Any]] = []
        for raw in raw_findings:
            if not isinstance(raw, Mapping):
                raise validation_error("Worker 审核结果 findings 包含非法项")
            finding = dict(raw)
            finding_type = str(finding.get("type") or "")
            if finding_type not in allowed_types:
                finding_type = allowed_types[0] if allowed_types else "content"
            file_id = str(finding.get("fileId") or "")
            if file_id not in allowed_file_ids:
                file_id = allowed_file_ids[0] if allowed_file_ids else ""
            if not file_id:
                # A review without evidence is represented by its summary, not a fabricated finding.
                continue
            severity = str(finding.get("severity") or "info")
            if severity not in BID_REVIEW_SEVERITIES:
                severity = "info"
            findings.append(
                {
                    "type": finding_type,
                    "severity": severity,
                    "title": str(finding.get("title") or "AI 审核提示"),
                    "description": str(finding.get("description") or "请人工复核该项内容"),
                    "fileId": file_id,
                    "page": finding.get("page"),
                    "excerpt": finding.get("excerpt"),
                    "suggestion": str(finding.get("suggestion") or "请按招标文件要求人工确认"),
                }
            )

        return cast(
            dict[str, Any],
            await self.apply_review_result(
                tenant_id=tenant_id,
                task_id=task_id,
                job_id=job_id,
                summary=str(output.get("summary") or "AI 审核完成，请人工确认关键结论"),
                findings=findings,
            ),
        )

    @_serialized_job_result
    async def apply_review_result(
        self,
        *,
        tenant_id: str,
        task_id: str,
        job_id: str,
        summary: str,
        findings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        cached = self.store.get_job_result(job_id, tenant_id=tenant_id, task_id=task_id, outcome="succeeded")
        if cached is not None:
            return cast(dict[str, Any], cached)
        self.store.assert_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_REVIEW,
        )
        self.store.assert_latest_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_REVIEW,
        )
        job_input = self.store.get_job_input(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_REVIEW,
        )
        allowed_review_types = set(job_input.get("reviewTypes") or [])
        allowed_file_ids = set(job_input.get("allowedFileIds") or [])
        task = self.store.get_task(task_id, tenant_id=tenant_id)
        if task.status != "ai_review":
            raise conflict("审核结果已过期或任务状态不匹配", currentStatus=task.status, jobId=job_id)
        report = self.store.get_review_report_by_job(job_id, tenant_id=tenant_id)
        if report.id != job_input.get("reportId"):
            raise conflict("审核结果与原始报告不匹配", jobId=job_id)
        now = _now()
        counts = {"error": 0, "warning": 0, "info": 0}
        prepared_findings: list[BidReviewFindingEntity] = []
        if not isinstance(findings, list):
            raise validation_error("审核结果 findings 必须为数组")
        for raw in findings:
            if not isinstance(raw, dict):
                raise validation_error("审核结果项必须为对象")
            finding_type = str(raw.get("type") or "")
            severity = str(raw.get("severity") or "")
            file_id = str(raw.get("fileId") or "").strip()
            if finding_type not in BID_REVIEW_TYPES or severity not in BID_REVIEW_SEVERITIES or not file_id:
                raise validation_error("审核结果字段不合法")
            if finding_type not in allowed_review_types or file_id not in allowed_file_ids:
                raise conflict("审核结果超出原始任务范围", jobId=job_id, fileId=file_id)
            page = raw.get("page")
            if page is not None and (isinstance(page, bool) or not isinstance(page, int) or page < 1):
                raise validation_error("审核结果 page 必须为正整数")
            file_obj = await self.files.get_file(tenant_id=tenant_id, file_id=file_id)
            _require_clean_file(file_obj)
            finding = BidReviewFindingEntity(
                id=new_id(),
                tenant_id=tenant_id,
                report_id=report.id,
                task_id=task_id,
                type=finding_type,
                severity=severity,
                title=str(raw.get("title") or "").strip(),
                description=str(raw.get("description") or "").strip(),
                file_id=file_id,
                page=page,
                excerpt=str(raw.get("excerpt") or "").strip() or None,
                suggestion=str(raw.get("suggestion") or "").strip(),
                created_at=now,
                updated_at=now,
            )
            if not finding.title:
                raise validation_error("审核结果 title 必填")
            prepared_findings.append(finding)
            counts["error" if severity in {"high", "critical"} else severity] += 1
        self.store.assert_latest_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_REVIEW,
        )
        for finding in prepared_findings:
            self.store.save_finding(finding)
        report.status = "succeeded"
        report.summary = str(summary).strip()
        report.counts = counts
        report.completed_at = now
        report.updated_at = now
        report.version += 1
        self.store.save_review_report(report)
        task.version += 1
        task.failed_stage = None
        task.updated_at = now
        self.store.save_task(task)
        response = review_report_dict(self.store.latest_review_for_task(task_id, tenant_id=tenant_id))
        if response is None:
            raise not_found("审核报告不存在", taskId=task_id)
        self.store.remember_job_result(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            outcome="succeeded",
            value=response,
        )
        await self._append_system_audit(
            tenant_id=tenant_id,
            task_id=task_id,
            job_id=job_id,
            action="bid_review.result_applied",
            summary="投标审核结果已落库",
        )
        return response

    @_serialized_job_result
    async def apply_document_result(
        self,
        *,
        tenant_id: str,
        task_id: str,
        job_id: str,
        files: list[dict[str, Any]],
        actor_id: str,
        actor_name: str,
    ) -> list[dict[str, Any]]:
        cached = self.store.get_job_result(job_id, tenant_id=tenant_id, task_id=task_id, outcome="succeeded")
        if cached is not None:
            return cast(list[dict[str, Any]], cached)
        self.store.assert_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_DOCUMENT_GENERATE,
        )
        self.store.assert_latest_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_DOCUMENT_GENERATE,
        )
        job_input = self.store.get_job_input(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_DOCUMENT_GENERATE,
        )
        if actor_id != job_input.get("actorId") or actor_name != job_input.get("actorName"):
            raise conflict("文档结果执行人和原始任务不匹配", jobId=job_id)
        expected_types = {"merged"} if job_input.get("mode") == "merged" else set(job_input.get("sections") or [])
        task = self.store.get_task(task_id, tenant_id=tenant_id)
        if task.status != "pending_output":
            raise conflict("文档结果已过期或任务状态不匹配", currentStatus=task.status, jobId=job_id)
        if not isinstance(files, list) or not files:
            raise validation_error("文档结果至少包含一个文件")
        prepared_files: list[tuple[str, Any, bytes, str, str]] = []
        seen_types: set[str] = set()
        for raw in files:
            if not isinstance(raw, dict):
                raise validation_error("文档结果项必须为对象")
            doc_type = str(raw.get("type") or "")
            file_id = str(raw.get("fileId") or "").strip()
            if doc_type not in BID_DOCUMENT_TYPES or not file_id:
                raise validation_error("文档结果 type 或 fileId 不合法")
            file_obj = await self.files.assert_accessible(
                tenant_id=tenant_id,
                file_id=file_id,
                actor_id=actor_id,
                purpose="bidDocument",
            )
            _require_clean_file(file_obj)
            if file_obj.mime_type != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                raise file_rejected("生成文档必须为 DOCX", fileId=file_id, mimeType=file_obj.mime_type)
            content = raw.get("content")
            if not isinstance(content, bytes):
                raise validation_error("文档 content 必须为真实 DOCX bytes")
            text_content = self.documents.validate_content(
                file_id=file_obj.id,
                size_bytes=file_obj.size_bytes,
                sha256=file_obj.sha256,
                content=content,
            )
            if doc_type in seen_types:
                raise validation_error("同一文档结果 type 不可重复")
            seen_types.add(doc_type)
            prepared_files.append(
                (
                    doc_type,
                    file_obj,
                    content,
                    text_content,
                    str(raw.get("changeSummary") or "生成新版本"),
                )
            )
        if seen_types != expected_types:
            raise conflict(
                "文档结果与原始生成范围不匹配",
                jobId=job_id,
                expectedTypes=sorted(expected_types),
                actualTypes=sorted(seen_types),
            )
        self.store.assert_latest_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_DOCUMENT_GENERATE,
        )
        for doc_type, file_obj, content, text_content, change_summary in prepared_files:
            self.documents.append_version(
                tenant_id=tenant_id,
                task_id=task_id,
                doc_type=doc_type,
                new_id_fn=new_id,
                file_id=file_obj.id,
                file_name=file_obj.file_name,
                size_bytes=file_obj.size_bytes,
                sha256=file_obj.sha256,
                content=content,
                text_content=text_content,
                change_summary=change_summary,
                created_by_id=actor_id,
                created_by_name=actor_name,
            )
        assert_transition(task.status, "completed")
        task.status = "completed"
        task.failed_stage = None
        task.current_step = step_for("completed")
        task.progress_percent = progress_for("completed")
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        response = self.documents.list_by_task(tenant_id=tenant_id, task_id=task_id)
        self.store.remember_job_result(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            outcome="succeeded",
            value=response,
        )
        await self._append_system_audit(
            tenant_id=tenant_id,
            task_id=task_id,
            job_id=job_id,
            action="bid_document.result_applied",
            summary="投标文档生成结果已落库",
        )
        await self.notifications.notify(
            NotificationInput(
                tenant_id=tenant_id,
                title="投标文档已生成",
                content=f"{task.project_name} 的投标文档已生成完成",
                user_id=task.assignee_id,
                resource_type="bid_task",
                resource_id=task_id,
            )
        )
        return response

    @_serialized_job_result
    async def apply_generated_document_result(
        self,
        *,
        tenant_id: str,
        task_id: str,
        job_id: str,
        worker_result: Mapping[str, Any],
        actor_id: str,
        actor_name: str,
    ) -> list[dict[str, Any]]:
        """Assemble an eager M7 result into real DOCX versions for the demo flow."""

        cached = self.store.get_job_result(job_id, tenant_id=tenant_id, task_id=task_id, outcome="succeeded")
        if cached is not None:
            return cast(list[dict[str, Any]], cached)
        self.store.assert_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_DOCUMENT_GENERATE,
        )
        self.store.assert_latest_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_DOCUMENT_GENERATE,
        )
        job_input = self.store.get_job_input(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_DOCUMENT_GENERATE,
        )
        if actor_id != job_input.get("actorId") or actor_name != job_input.get("actorName"):
            raise conflict("文档结果执行人和原始任务不匹配", jobId=job_id)
        if str(worker_result.get("status") or "") != "succeeded":
            raise conflict("Worker 未成功完成，不能装配文档", jobId=job_id)
        worker_job_id = str(worker_result.get("jobId") or job_id)
        if worker_job_id != job_id:
            raise conflict("Worker 结果与原始任务不匹配", jobId=job_id, workerJobId=worker_job_id)
        worker_output = worker_result.get("output")
        if not isinstance(worker_output, Mapping):
            raise validation_error("Worker 文档结果缺少 output 对象")
        requested_technical = job_input.get("technicalDocument")
        if requested_technical and not isinstance(worker_output.get("technicalDocument"), Mapping):
            raise validation_error("逐段技术文档结果缺失，未创建占位 DOCX")

        task = self.store.get_task(task_id, tenant_id=tenant_id)
        if task.status != "pending_output":
            raise conflict("文档结果已过期或任务状态不匹配", currentStatus=task.status, jobId=job_id)
        embedded_images = await self._load_reference_images(
            tenant_id=tenant_id,
            actor_id=actor_id,
            technical_document=requested_technical,
        )
        requested_sections = [str(item) for item in (job_input.get("sections") or [])]
        document_types = ["merged"] if job_input.get("mode") == "merged" else requested_sections
        template_name = "标准投标模板"
        technical_output = worker_output.get("technicalDocument")
        if isinstance(technical_output, Mapping):
            template_name = str(technical_output.get("templateName") or template_name)
        elif isinstance(requested_technical, Mapping):
            template_name = str(requested_technical.get("templateName") or template_name)

        generated_files: list[tuple[str, str, bytes, str]] = []
        labels = {"qualification": "资格标", "commercial": "商务标", "technical": "技术标", "merged": "合并标书"}
        for doc_type in document_types:
            section_types = requested_sections if doc_type == "merged" else [doc_type]
            document_sections: list[dict[str, Any]] = []
            for section_type in section_types:
                document_sections.extend(_fallback_document_sections(task, section_type, worker_output))
            built = build_bid_docx(
                title=f"{task.project_name} · {labels.get(doc_type, doc_type)}",
                template_name=template_name,
                sections=document_sections,
                images=embedded_images,
                include_watermark=bool(job_input.get("includeWatermark")),
            )
            suffix = f"；缺失图片 {', '.join(built.missing_image_ids)}" if built.missing_image_ids else ""
            generated_files.append(
                (
                    doc_type,
                    f"{_safe_document_name(task.project_name)}-{doc_type}.docx",
                    built.content,
                    f"AI 逐段生成；嵌入图片 {built.embedded_image_count} 张{suffix}",
                )
            )

        for doc_type, file_name, content, change_summary in generated_files:
            file_id = new_id()
            self.documents.append_version(
                tenant_id=tenant_id,
                task_id=task_id,
                doc_type=doc_type,
                new_id_fn=new_id,
                file_id=file_id,
                file_name=file_name,
                size_bytes=len(content),
                sha256=sha256(content).hexdigest(),
                content=content,
                change_summary=change_summary,
                created_by_id=actor_id,
                created_by_name=actor_name,
            )

        assert_transition(task.status, "completed")
        task.status = "completed"
        task.failed_stage = None
        task.current_step = step_for("completed")
        task.progress_percent = progress_for("completed")
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        response = self.documents.list_by_task(tenant_id=tenant_id, task_id=task_id)
        self.store.remember_job_result(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            outcome="succeeded",
            value=response,
        )
        await self._append_system_audit(
            tenant_id=tenant_id,
            task_id=task_id,
            job_id=job_id,
            action="bid_document.ai_result_assembled",
            summary=f"AI 逐段结果已装配为 {len(generated_files)} 份 DOCX",
        )
        await self.notifications.notify(
            NotificationInput(
                tenant_id=tenant_id,
                title="投标文档已生成",
                content=f"{task.project_name} 的 AI 投标文档已生成并可下载",
                user_id=task.assignee_id,
                resource_type="bid_task",
                resource_id=task_id,
            )
        )
        return response

    async def _load_reference_images(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        technical_document: Any,
    ) -> dict[str, EmbeddedImage]:
        if not isinstance(technical_document, Mapping):
            return {}
        raw_images = technical_document.get("referenceImages")
        if not isinstance(raw_images, list) or not raw_images:
            return {}
        loaded: dict[str, EmbeddedImage] = {}
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            for raw_image in raw_images:
                if not isinstance(raw_image, Mapping):
                    continue
                file_id = str(raw_image.get("fileId") or "").strip()
                if not file_id or file_id in loaded:
                    continue
                try:
                    file_obj = await self.files.assert_accessible(
                        tenant_id=tenant_id,
                        file_id=file_id,
                        actor_id=actor_id,
                        purpose="bidIllustration",
                    )
                    _require_clean_file(file_obj)
                    if file_obj.mime_type not in {"image/png", "image/jpeg"}:
                        raise ValueError(f"unsupported image MIME type: {file_obj.mime_type}")
                    if file_obj.size_bytes > 20 * 1024 * 1024:
                        raise ValueError("reference image exceeds 20 MiB")
                    download_url = file_obj.download_url or await self.files.get_download_url(
                        tenant_id=tenant_id,
                        file_id=file_id,
                        expires_minutes=15,
                    )
                    if not download_url or not download_url.startswith(("http://", "https://")):
                        raise ValueError("reference image has no trusted download URL")
                    response = await client.get(download_url)
                    response.raise_for_status()
                    content = response.content
                    if len(content) != file_obj.size_bytes:
                        raise ValueError("reference image size does not match metadata")
                    if sha256(content).hexdigest().lower() != file_obj.sha256.lower():
                        raise ValueError("reference image digest does not match metadata")
                    loaded[file_id] = EmbeddedImage(
                        file_id=file_id,
                        content=content,
                        mime_type=file_obj.mime_type,
                    )
                except Exception:
                    logger.warning("unable to embed bid illustration %s", file_id, exc_info=True)
        return loaded

    @_serialized_job_result
    async def apply_document_rollback_result(
        self,
        *,
        tenant_id: str,
        task_id: str,
        job_id: str,
        target_version_id: str,
        reason: str,
        actor_id: str,
        actor_name: str,
    ) -> dict[str, Any]:
        cached = self.store.get_job_result(job_id, tenant_id=tenant_id, task_id=task_id, outcome="succeeded")
        if cached is not None:
            return cast(dict[str, Any], cached)
        self.store.assert_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_DOCUMENT_ROLLBACK,
        )
        self.store.assert_latest_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_DOCUMENT_ROLLBACK,
        )
        job_input = self.store.get_job_input(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=JOB_TYPE_DOCUMENT_ROLLBACK,
        )
        task = self.store.get_task(task_id, tenant_id=tenant_id)
        _require_task_status(task, {"pending_output", "completed"})
        normalized_reason = str(reason).strip()
        if not normalized_reason:
            raise validation_error("reason 必填")
        if (
            target_version_id != job_input.get("versionId")
            or normalized_reason != job_input.get("reason")
            or actor_id != job_input.get("actorId")
            or actor_name != job_input.get("actorName")
        ):
            raise conflict("回滚结果与原始任务输入不匹配", jobId=job_id)
        target = self.documents.store.get_version(target_version_id, tenant_id=tenant_id)
        document = self.documents.store.get_document(target.document_id, tenant_id=tenant_id)
        if document.task_id != task_id:
            raise not_found("文档版本不属于该任务", versionId=target_version_id)
        version = self.documents.rollback_to(
            tenant_id=tenant_id,
            task_id=task_id,
            document_id=document.id,
            target_version_id=target_version_id,
            new_id_fn=new_id,
            reason=normalized_reason,
            actor_id=actor_id,
            actor_name=actor_name,
        )
        from app.domains.documents.mappers import document_version_dict

        response = document_version_dict(version)
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        self.store.remember_job_result(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            outcome="succeeded",
            value=response,
        )
        await self._append_system_audit(
            tenant_id=tenant_id,
            task_id=task_id,
            job_id=job_id,
            action="bid_document.rollback_applied",
            summary=f"文档已回滚为新版本 v{version.version_number}",
        )
        return response

    @_serialized_job_result
    async def apply_job_failure(
        self,
        *,
        tenant_id: str,
        task_id: str,
        job_id: str,
        failed_stage: str,
        message: str,
    ) -> dict[str, Any]:
        cached = self.store.get_job_result(job_id, tenant_id=tenant_id, task_id=task_id, outcome="failed")
        if cached is not None:
            return cast(dict[str, Any], cached)
        task = self.store.get_task(task_id, tenant_id=tenant_id)
        if failed_stage not in {"parsing", "material_prep", "ai_review", "pending_output"}:
            raise validation_error("failedStage 不合法")
        actual_action = self.store.get_job_action(job_id, tenant_id=tenant_id, task_id=task_id)
        self.store.assert_latest_job(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            action=actual_action,
        )
        if actual_action == JOB_TYPE_DOCUMENT_ROLLBACK:
            if failed_stage != "pending_output" or task.status not in {"pending_output", "completed"}:
                raise conflict(
                    "文档回滚失败结果与任务状态不匹配",
                    currentStatus=task.status,
                    jobId=job_id,
                    failedStage=failed_stage,
                )
            response = task_summary_dict(task)
            self.store.remember_job_result(
                job_id,
                tenant_id=tenant_id,
                task_id=task_id,
                outcome="failed",
                value=response,
            )
            await self._append_system_audit(
                tenant_id=tenant_id,
                task_id=task_id,
                job_id=job_id,
                action="bid_document.rollback_failed",
                summary=str(message).strip() or "文档回滚失败",
            )
            await self.notifications.notify(
                NotificationInput(
                    tenant_id=tenant_id,
                    title="文档回滚失败",
                    content=f"{task.project_name}：{str(message).strip() or '文档回滚失败'}",
                    user_id=task.assignee_id,
                    resource_type="bid_task",
                    resource_id=task_id,
                )
            )
            return response
        allowed_actions = {
            "parsing": {JOB_TYPE_TENDER_PARSE},
            "material_prep": {JOB_TYPE_MATERIAL_MATCH, JOB_TYPE_TEMPLATE_GENERATE},
            "ai_review": {JOB_TYPE_REVIEW},
            "pending_output": {JOB_TYPE_DOCUMENT_GENERATE},
        }
        if actual_action not in allowed_actions[failed_stage]:
            raise conflict("失败结果与任务阶段不匹配", jobId=job_id, failedStage=failed_stage)
        if task.status != failed_stage:
            raise conflict("失败结果已过期或任务状态不匹配", currentStatus=task.status, jobId=job_id)
        assert_transition(task.status, "failed")
        task.status = "failed"
        task.failed_stage = failed_stage
        task.current_step = step_for(failed_stage)
        task.progress_percent = 0
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        if failed_stage == "ai_review":
            try:
                report = self.store.get_review_report_by_job(job_id, tenant_id=tenant_id)
            except DomainError:
                report = None
            if report is not None:
                report.status = "failed"
                report.summary = str(message).strip()
                report.updated_at = _now()
                self.store.save_review_report(report)
        response = task_summary_dict(task)
        self.store.remember_job_result(
            job_id,
            tenant_id=tenant_id,
            task_id=task_id,
            outcome="failed",
            value=response,
        )
        await self._append_system_audit(
            tenant_id=tenant_id,
            task_id=task_id,
            job_id=job_id,
            action="bid_task.job_failed",
            summary=str(message).strip() or "异步任务执行失败",
        )
        await self.notifications.notify(
            NotificationInput(
                tenant_id=tenant_id,
                title="投标任务处理失败",
                content=f"{task.project_name}：{str(message).strip() or '异步任务执行失败'}",
                user_id=task.assignee_id,
                resource_type="bid_task",
                resource_id=task_id,
            )
        )
        return response

    async def bind_material_file(
        self,
        actor: AuthPrincipal,
        task_id: str,
        material_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_member_or_owner(actor, task)
        _require_task_status(task, {"draft", "material_prep", "failed"})
        material = self.store.get_material(material_id, tenant_id=actor.tenant_id)
        if material.task_id != task_id:
            raise not_found("材料不属于该任务", materialId=material_id)
        if not isinstance(payload, dict) or set(payload) - {"fileId"}:
            raise validation_error("请求体包含未定义字段")
        file_id = payload.get("fileId")
        if not file_id or not isinstance(file_id, str):
            raise validation_error("fileId 必填")
        file_obj = await self.files.assert_accessible(
            tenant_id=actor.tenant_id,
            file_id=file_id.strip(),
            actor_id=actor.user_id,
            purpose="bidMaterial",
        )
        _require_clean_file(file_obj)
        _bind_material_file(material, file_obj)
        material.status = "have"
        material.version += 1
        material.updated_at = _now()
        saved = self.store.save_material(material)
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        await self._append_audit(
            actor,
            task_id,
            "bid_material.file_bound",
            f"绑定材料文件 {material_id}",
            target_type="bid_material",
            target_id=material_id,
        )
        return material_dict(saved)

    async def unbind_material_file(self, actor: AuthPrincipal, task_id: str, material_id: str) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_member_or_owner(actor, task)
        _require_task_status(task, {"draft", "material_prep", "failed"})
        material = self.store.get_material(material_id, tenant_id=actor.tenant_id)
        if material.task_id != task_id:
            raise not_found("材料不属于该任务", materialId=material_id)
        material.file_id = None
        material.file_name = None
        material.mime_type = None
        material.size_bytes = 0
        material.sha256 = None
        material.file_scan_status = None
        material.file_created_at = None
        material.file_preview_url = None
        material.file_download_url = None
        material.status = "pending"
        material.version += 1
        material.updated_at = _now()
        saved = self.store.save_material(material)
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        await self._append_audit(
            actor,
            task_id,
            "bid_material.file_unbound",
            f"解绑材料文件 {material_id}",
            target_type="bid_material",
            target_id=material_id,
        )
        return material_dict(saved)

    async def batch_bind(
        self,
        actor: AuthPrincipal,
        task_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_member_or_owner(actor, task)
        _require_task_status(task, {"draft", "material_prep", "failed"})
        cleaned = validate_batch_bind(payload)
        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        for binding in cleaned["bindings"]:
            try:
                material = self.store.get_material(binding["materialId"], tenant_id=actor.tenant_id)
                if material.task_id != task_id:
                    failed.append(
                        {"materialId": binding["materialId"], "code": "NOT_FOUND", "message": "材料不属于该任务"}
                    )
                    continue
                if not cleaned["replaceExisting"] and material.file_id:
                    failed.append(
                        {
                            "materialId": material.id,
                            "code": "CONFLICT",
                            "message": "材料已绑定文件，需 replaceExisting=true",
                        }
                    )
                    continue
                file_obj = await self.files.assert_accessible(
                    tenant_id=actor.tenant_id,
                    file_id=binding["fileId"],
                    actor_id=actor.user_id,
                    purpose="bidMaterial",
                )
                _require_clean_file(file_obj)
                _bind_material_file(material, file_obj)
                material.status = "have"
                material.version += 1
                material.updated_at = _now()
                self.store.save_material(material)
                succeeded.append(material.id)
            except Exception as exc:  # 捕获域错误
                from app.domains.bids.errors import DomainError

                if isinstance(exc, DomainError):
                    failed.append({"materialId": binding["materialId"], "code": exc.code, "message": exc.message})
                else:
                    failed.append(
                        {
                            "materialId": binding["materialId"],
                            "code": "INTERNAL_ERROR",
                            "message": "绑定失败",
                        }
                    )
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        await self._append_audit(actor, task_id, "bid_material.batch_bound", "批量绑定材料文件")
        return {"succeeded": succeeded, "failed": failed}

    async def export_materials(
        self,
        actor: AuthPrincipal,
        task_id: str,
        *,
        category: str | None = None,
        status: str | None = None,
        required: bool | None = None,
    ) -> bytes:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_viewer(actor, task)
        items = self.store.list_materials(
            tenant_id=actor.tenant_id,
            task_id=task_id,
            category=category,
            status=status,
            required=required,
        )
        return export_materials_xlsx(items, project_name=task.project_name)

    @_serialized_enqueue
    async def enqueue_template_generate(
        self,
        actor: AuthPrincipal,
        task_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        key = require_idempotency_key(idempotency_key)
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_viewer(actor, task)
        scoped_key = _idempotency_scope(
            action=JOB_TYPE_TEMPLATE_GENERATE,
            tenant_id=actor.tenant_id,
            actor_id=actor.user_id,
            aggregate_id=task_id,
            key=key,
        )
        cached = self.store.get_idempotency(scoped_key)
        if cached is not None:
            return cast(dict[str, Any], cached)
        _require_task_status(task, {"material_prep", "failed"})
        _require_retry_stage(task, "material_prep")
        if not isinstance(payload, dict) or set(payload) - {"materialIds"}:
            raise validation_error("请求体包含未定义字段")
        material_ids = payload.get("materialIds") if isinstance(payload, dict) else None
        if not isinstance(material_ids, list) or not material_ids:
            raise validation_error(
                "materialIds 必填且至少 1 项",
                field_errors=[{"field": "materialIds", "code": "REQUIRED", "message": "materialIds 必填"}],
            )
        cleaned = [str(x).strip() for x in material_ids if str(x).strip()]
        if not cleaned or len(cleaned) != len(set(cleaned)):
            raise validation_error("materialIds 必须非空且不可重复")
        material_snapshots: list[dict[str, Any]] = []
        for material_id in cleaned:
            material = self.store.get_material(material_id, tenant_id=actor.tenant_id)
            if material.task_id != task_id:
                raise not_found("材料不属于该任务", materialId=material_id)
            material_snapshots.append(
                {
                    "materialId": material.id,
                    "version": material.version,
                    "fileId": material.file_id,
                    "sha256": material.sha256,
                }
            )
        original = copy.deepcopy(task)
        if task.status == "failed":
            assert_transition(task.status, "material_prep")
            task.status = "material_prep"
            task.failed_stage = None
            task.current_step = step_for("material_prep")
            task.progress_percent = progress_for("material_prep")
            task.version += 1
            task.updated_at = _now()
            self.store.save_task(task)
        try:
            job = await self.jobs.enqueue(
                tenant_id=actor.tenant_id,
                job_type="ai_analysis",
                payload=_new_job_payload(
                    m5_job_type=JOB_TYPE_TEMPLATE_GENERATE,
                    tenant_id=actor.tenant_id,
                    task_id=task_id,
                    actor_id=actor.user_id,
                    extra={"materialIds": cleaned, "materialSnapshots": material_snapshots},
                ),
                created_by=actor.user_id,
                project_id=task_id,
                idempotency_key=key,
            )
        except Exception:
            self.store.save_task(original)
            raise
        self.store.remember_job(
            job.id,
            tenant_id=actor.tenant_id,
            task_id=task_id,
            action=JOB_TYPE_TEMPLATE_GENERATE,
            input_data={
                "materialIds": cleaned,
                "materialSnapshots": material_snapshots,
                "actorId": actor.user_id,
            },
        )
        response = _job_dict(job)
        self.store.remember_idempotency(scoped_key, response)
        await self._append_audit(actor, task_id, "bid_material.template_enqueued", f"发起模板生成 Job {job.id}")
        return response

    # ============================================================
    # 审核
    # ============================================================
    @_serialized_enqueue
    async def enqueue_review(
        self,
        actor: AuthPrincipal,
        task_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        key = require_idempotency_key(idempotency_key)
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_reviewer(actor, task)
        scoped_key = _idempotency_scope(
            action=JOB_TYPE_REVIEW,
            tenant_id=actor.tenant_id,
            actor_id=actor.user_id,
            aggregate_id=task_id,
            key=key,
        )
        cached = self.store.get_idempotency(scoped_key)
        if cached is not None:
            return cast(dict[str, Any], cached)
        cleaned = validate_create_review(payload)
        allowed_file_ids: set[str] = set()
        for version_id in cleaned["fileVersionIds"]:
            version = self.documents.store.get_version(version_id, tenant_id=actor.tenant_id)
            document = self.documents.store.get_document(version.document_id, tenant_id=actor.tenant_id)
            if document.task_id != task_id:
                raise not_found("文档版本不属于该任务", versionId=version_id)
            allowed_file_ids.add(version.file_id)
        if not cleaned["fileVersionIds"]:
            if task.tender_file_id:
                allowed_file_ids.add(task.tender_file_id)
            allowed_file_ids.update(material.file_id for material in task.materials if material.file_id)
            allowed_file_ids.update(
                version.file_id
                for version in self.documents.store.list_versions_by_task(
                    tenant_id=actor.tenant_id,
                    task_id=task_id,
                )
            )
        _require_retry_stage(task, "ai_review")
        assert_transition(task.status, "ai_review")
        original = copy.deepcopy(task)
        now = _now()
        report = BidReviewReportEntity(
            id=new_id(),
            tenant_id=actor.tenant_id,
            task_id=task_id,
            status="queued",
            created_at=now,
            updated_at=now,
        )
        self.store.save_review_report(report)
        # 切到 ai_review
        task.status = "ai_review"
        task.failed_stage = None
        task.current_step = step_for("ai_review")
        task.progress_percent = progress_for("ai_review")
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        try:
            job = await self.jobs.enqueue(
                tenant_id=actor.tenant_id,
                job_type="ai_analysis",
                payload=_new_job_payload(
                    m5_job_type=JOB_TYPE_REVIEW,
                    tenant_id=actor.tenant_id,
                    task_id=task_id,
                    actor_id=actor.user_id,
                    extra={
                        "reviewTypes": cleaned["types"],
                        "fileVersionIds": cleaned["fileVersionIds"],
                        "reportId": report.id,
                    },
                ),
                created_by=actor.user_id,
                project_id=task_id,
                idempotency_key=key,
            )
        except Exception:
            self.store.save_task(original)
            self.store.remove_review_report(report.id, tenant_id=actor.tenant_id)
            raise
        report.job_id = job.id
        report.updated_at = _now()
        self.store.save_review_report(report)
        self.store.remember_job(
            job.id,
            tenant_id=actor.tenant_id,
            task_id=task_id,
            action=JOB_TYPE_REVIEW,
            input_data={
                "reviewTypes": cleaned["types"],
                "fileVersionIds": cleaned["fileVersionIds"],
                "allowedFileIds": sorted(allowed_file_ids),
                "reportId": report.id,
                "actorId": actor.user_id,
            },
        )
        response = _job_dict(job)
        if job.status == "succeeded" and isinstance(job.result, Mapping):
            await self.apply_generated_review_result(
                tenant_id=actor.tenant_id,
                task_id=task_id,
                job_id=job.id,
                worker_result=job.result,
            )
        elif job.status == "failed":
            message = str((job.error or {}).get("message") or "投标审核 Worker 执行失败")
            await self.apply_job_failure(
                tenant_id=actor.tenant_id,
                task_id=task_id,
                job_id=job.id,
                failed_stage="ai_review",
                message=message,
            )
        self.store.remember_idempotency(scoped_key, response)
        await self._append_audit(actor, task_id, "bid_review.enqueued", f"发起投标审核 Job {job.id}")
        return response

    async def latest_review(self, actor: AuthPrincipal, task_id: str) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_viewer(actor, task)
        report = self.store.latest_review_for_task(task_id, tenant_id=actor.tenant_id)
        if report is None:
            raise not_found("暂无审核报告", taskId=task_id)
        return review_report_dict(report)  # type: ignore[return-value]

    async def decide_finding(
        self,
        actor: AuthPrincipal,
        task_id: str,
        finding_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_reviewer(actor, task)
        _require_task_status(task, {"ai_review"})
        finding = self.store.get_finding(finding_id, tenant_id=actor.tenant_id)
        if finding.task_id != task_id:
            raise not_found("审核发现不属于该任务", findingId=finding_id)
        cleaned = validate_review_decision(payload)
        finding.decision = cleaned["decision"]
        finding.decision_comment = cleaned["comment"]
        finding.decided_by_id = actor.user_id
        finding.decided_by_name = actor.name
        finding.decided_at = _now()
        finding.version += 1
        finding.updated_at = _now()
        saved = self.store.save_finding(finding)
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="bid_task",
                aggregate_id=task_id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="bid_review.decision",
                summary=f"处理审核发现 {finding_id} → {saved.decision}",
            )
        )
        return review_finding_dict(saved)

    # ============================================================
    # 文档（编排 + 委托 documents 域）
    # ============================================================
    @_serialized_enqueue
    async def enqueue_document_generate(
        self,
        actor: AuthPrincipal,
        task_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        key = require_idempotency_key(idempotency_key)
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_owner(actor, task)
        scoped_key = _idempotency_scope(
            action=JOB_TYPE_DOCUMENT_GENERATE,
            tenant_id=actor.tenant_id,
            actor_id=actor.user_id,
            aggregate_id=task_id,
            key=key,
        )
        cached = self.store.get_idempotency(scoped_key)
        if cached is not None:
            return cast(dict[str, Any], cached)
        if task.status not in {"ai_review", "failed"}:
            raise conflict(
                "当前状态不可发起文档生成",
                currentStatus=task.status,
            )
        _require_retry_stage(task, "pending_output")
        cleaned = validate_document_generate(payload)
        generation_context = _generation_context(task)
        latest_review = self.store.latest_review_for_task(task_id, tenant_id=actor.tenant_id)
        if latest_review is None or latest_review.status != "succeeded":
            raise conflict("审核尚未成功完成，不能生成投标文档", currentStatus=task.status)
        unresolved = [
            finding.id
            for finding in latest_review.findings
            if finding.severity in {"high", "critical"} and finding.decision == "pending"
        ]
        if unresolved:
            raise conflict("存在未处理的高风险审核发现", findingIds=unresolved)
        original = copy.deepcopy(task)
        # 进入 pending_output
        assert_transition(task.status, "pending_output")
        task.status = "pending_output"
        task.failed_stage = None
        task.current_step = step_for("pending_output")
        task.progress_percent = progress_for("pending_output")
        task.version += 1
        task.updated_at = _now()
        self.store.save_task(task)
        try:
            job = await self.jobs.enqueue(
                tenant_id=actor.tenant_id,
                job_type="document_generation",
                payload=_new_job_payload(
                    m5_job_type=JOB_TYPE_DOCUMENT_GENERATE,
                    tenant_id=actor.tenant_id,
                    task_id=task_id,
                    actor_id=actor.user_id,
                    extra={
                        "mode": cleaned["mode"],
                        "sections": cleaned["sections"],
                        "templateMode": cleaned["templateMode"],
                        "documentTemplateId": cleaned["documentTemplateId"],
                        "includeWatermark": cleaned["includeWatermark"],
                        "technicalDocument": cleaned["technicalDocument"],
                        **generation_context,
                    },
                ),
                created_by=actor.user_id,
                project_id=task_id,
                idempotency_key=key,
            )
        except Exception:
            self.store.save_task(original)
            raise
        self.store.remember_job(
            job.id,
            tenant_id=actor.tenant_id,
            task_id=task_id,
            action=JOB_TYPE_DOCUMENT_GENERATE,
            input_data={
                "mode": cleaned["mode"],
                "sections": cleaned["sections"],
                "templateMode": cleaned["templateMode"],
                "documentTemplateId": cleaned["documentTemplateId"],
                "includeWatermark": cleaned["includeWatermark"],
                "technicalDocument": cleaned["technicalDocument"],
                "actorId": actor.user_id,
                "actorName": actor.name,
            },
        )
        response = _job_dict(job)
        if job.status == "succeeded" and isinstance(job.result, Mapping):
            await self.apply_generated_document_result(
                tenant_id=actor.tenant_id,
                task_id=task_id,
                job_id=job.id,
                worker_result=job.result,
                actor_id=actor.user_id,
                actor_name=actor.name,
            )
        elif job.status == "failed":
            message = str((job.error or {}).get("message") or "文档生成 Worker 执行失败")
            await self.apply_job_failure(
                tenant_id=actor.tenant_id,
                task_id=task_id,
                job_id=job.id,
                failed_stage="pending_output",
                message=message,
            )
        self.store.remember_idempotency(scoped_key, response)
        await self._append_audit(actor, task_id, "bid_document.generate_enqueued", f"发起文档生成 Job {job.id}")
        return response

    async def list_documents(self, actor: AuthPrincipal, task_id: str) -> list[dict[str, Any]]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_viewer(actor, task)
        return self.documents.list_by_task(tenant_id=actor.tenant_id, task_id=task_id)

    async def download_document(
        self, actor: AuthPrincipal, task_id: str, document_id: str
    ) -> tuple[bytes | None, str | None, str, str, str]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_viewer(actor, task)
        doc = self.documents.store.get_document(document_id, tenant_id=actor.tenant_id)
        if doc.task_id != task_id:
            raise not_found("文档不属于该投标任务", documentId=document_id)
        if not doc.versions:
            raise not_found("文档尚未生成任何版本", documentId=document_id)
        latest = doc.versions[-1]
        download_url = None
        if latest.content is None:
            download_url = await self.files.get_download_url(
                tenant_id=actor.tenant_id,
                file_id=latest.file_id,
            )
            if download_url is None:
                raise not_found("文档文件暂不可下载", documentId=document_id)
        return latest.content, download_url, latest.file_name, latest.sha256, latest.mime_type

    async def list_document_versions(
        self,
        actor: AuthPrincipal,
        task_id: str,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_viewer(actor, task)
        return self.documents.list_versions_by_task(
            tenant_id=actor.tenant_id,
            task_id=task_id,
            page=page,
            page_size=page_size,
        )

    async def compare_document_versions(
        self,
        actor: AuthPrincipal,
        task_id: str,
        from_version_id: str,
        to_version_id: str,
    ) -> dict[str, Any]:
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_viewer(actor, task)
        return self.documents.compare_versions(
            tenant_id=actor.tenant_id,
            task_id=task_id,
            from_version_id=from_version_id,
            to_version_id=to_version_id,
        )

    @_serialized_enqueue
    async def enqueue_document_rollback(
        self,
        actor: AuthPrincipal,
        task_id: str,
        version_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        key = require_idempotency_key(idempotency_key)
        task = self.store.get_task(task_id, tenant_id=actor.tenant_id)
        require_owner(actor, task)
        scoped_key = _idempotency_scope(
            action=JOB_TYPE_DOCUMENT_ROLLBACK,
            tenant_id=actor.tenant_id,
            actor_id=actor.user_id,
            aggregate_id=task_id,
            key=key,
        )
        cached = self.store.get_idempotency(scoped_key)
        if cached is not None:
            return cast(dict[str, Any], cached)
        _require_task_status(task, {"pending_output", "completed"})
        if not isinstance(payload, dict) or set(payload) - {"reason"}:
            raise validation_error("请求体包含未定义字段")
        reason = (payload.get("reason") if isinstance(payload, dict) else "") or ""
        reason = str(reason).strip()
        if not reason:
            raise validation_error("reason 必填")
        # 仅校验目标；成功 JobResult 到达后再创建新版本，避免派发失败却提前改历史。
        version = self.documents.store.get_version(version_id, tenant_id=actor.tenant_id)
        document = self.documents.store.get_document(version.document_id, tenant_id=actor.tenant_id)
        if document.task_id != task_id:
            raise not_found("文档版本不属于该任务", versionId=version_id)
        job = await self.jobs.enqueue(
            tenant_id=actor.tenant_id,
            job_type="document_generation",
            payload=_new_job_payload(
                m5_job_type=JOB_TYPE_DOCUMENT_ROLLBACK,
                tenant_id=actor.tenant_id,
                task_id=task_id,
                actor_id=actor.user_id,
                extra={"versionId": version_id, "reason": reason},
            ),
            created_by=actor.user_id,
            project_id=task_id,
            idempotency_key=key,
        )
        self.store.remember_job(
            job.id,
            tenant_id=actor.tenant_id,
            task_id=task_id,
            action=JOB_TYPE_DOCUMENT_ROLLBACK,
            input_data={
                "versionId": version_id,
                "reason": reason,
                "actorId": actor.user_id,
                "actorName": actor.name,
            },
        )
        response = _job_dict(job)
        self.store.remember_idempotency(scoped_key, response)
        await self._append_audit(actor, task_id, "bid_document.rollback_enqueued", f"发起文档回滚 Job {job.id}")
        return response
