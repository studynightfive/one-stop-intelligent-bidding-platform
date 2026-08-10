"""M5 实体 -> OpenAPI 契约 camelCase 字典。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domains.bids.entities import (
    BidMaterialEntity,
    BidReviewFindingEntity,
    BidReviewReportEntity,
    BidTaskAssignmentEntity,
    BidTaskEntity,
    TenderRequirementsEntity,
)


def _dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.isoformat() + "Z"
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _file_ref(material: BidMaterialEntity | None) -> dict[str, Any] | None:
    if material is None or not material.file_id:
        return None
    data: dict[str, Any] = {
        "id": material.file_id,
        "fileName": material.file_name or "",
        "mimeType": material.mime_type or "application/octet-stream",
        "sizeBytes": int(material.size_bytes or 0),
        "sha256": material.sha256 or "0" * 64,
        "scanStatus": material.file_scan_status or "clean",
        "createdAt": _dt(material.file_created_at or material.updated_at or material.created_at),
    }
    if material.file_preview_url:
        data["previewUrl"] = material.file_preview_url
    if material.file_download_url:
        data["downloadUrl"] = material.file_download_url
    return data


def assignment_dict(item: BidTaskAssignmentEntity) -> dict[str, Any]:
    return {
        "taskId": item.task_id,
        "user": {"id": item.user_id, "name": item.user_name},
        "roleInTask": item.role_in_task,
        "assignedAt": _dt(item.assigned_at),
    }


def material_dict(item: BidMaterialEntity) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": item.id,
        "taskId": item.task_id,
        "name": item.name,
        "category": item.category,
        "requirement": item.requirement,
        "status": item.status,
        "required": item.required,
        "sortOrder": item.sort_order,
        "source": item.source,
        "version": item.version,
    }
    if item.source_id:
        data["sourceId"] = item.source_id
    if item.match_confidence is not None:
        data["matchConfidence"] = item.match_confidence
    if item.file_id:
        data["file"] = _file_ref(item)
    return data


def requirements_dict(entity: TenderRequirementsEntity | None) -> dict[str, Any]:
    if entity is None:
        return {
            "projectInfo": {},
            "scoringItems": [],
            "disqualificationItems": [],
            "qualificationRequirements": [],
            "technicalRequirements": [],
            "version": 1,
        }
    return {
        "projectInfo": entity.project_info,
        "scoringItems": entity.scoring_items,
        "disqualificationItems": entity.disqualification_items,
        "qualificationRequirements": entity.qualification_requirements,
        "technicalRequirements": entity.technical_requirements,
        "version": entity.version,
    }


def task_summary_dict(entity: BidTaskEntity) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": entity.id,
        "projectName": entity.project_name,
        "tenderNo": entity.tender_no,
        "tenderEntity": entity.tender_entity,
        "deadline": _dt(entity.deadline),
        "status": entity.status,
        "currentStep": entity.current_step,
        "progressPercent": entity.progress_percent,
        "assignee": {"id": entity.assignee_id, "name": entity.assignee_name},
        "tags": list(entity.tags),
        "materialSummary": entity.material_summary,
        "version": entity.version,
        "createdAt": _dt(entity.created_at),
        "updatedAt": _dt(entity.updated_at),
    }
    if entity.linked_evaluation_id:
        data["linkedEvaluationId"] = entity.linked_evaluation_id
    return data


def task_detail_dict(
    entity: BidTaskEntity,
    *,
    documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    data = task_summary_dict(entity)
    if entity.tender_file_id:
        tender_file: dict[str, Any] = {
            "id": entity.tender_file_id,
            "fileName": entity.tender_file_name or "",
            "mimeType": entity.tender_mime_type or "application/octet-stream",
            "sizeBytes": entity.tender_size_bytes,
            "sha256": entity.tender_sha256 or "0" * 64,
            "scanStatus": entity.tender_scan_status or "clean",
            "createdAt": _dt(entity.tender_file_created_at or entity.updated_at or entity.created_at),
        }
        if entity.tender_preview_url:
            tender_file["previewUrl"] = entity.tender_preview_url
        if entity.tender_download_url:
            tender_file["downloadUrl"] = entity.tender_download_url
        data["tenderFile"] = tender_file
    else:
        data["tenderFile"] = None
    if entity.linked_evaluation_id:
        data["linkedEvaluationId"] = entity.linked_evaluation_id
    data["assignments"] = [assignment_dict(a) for a in entity.assignments]
    data["requirements"] = requirements_dict(entity.requirements)
    data["latestReview"] = review_report_dict(entity.latest_review) if entity.latest_review else None
    data["documents"] = documents or []
    return data


def review_finding_dict(item: BidReviewFindingEntity) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": item.id,
        "type": item.type,
        "severity": item.severity,
        "title": item.title,
        "description": item.description,
        "fileId": item.file_id,
        "suggestion": item.suggestion,
        "decision": item.decision,
        "version": item.version,
    }
    if item.page is not None:
        data["page"] = item.page
    if item.excerpt:
        data["excerpt"] = item.excerpt
    return data


def review_report_dict(item: BidReviewReportEntity | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {
        "id": item.id,
        "taskId": item.task_id,
        "status": item.status,
        "summary": item.summary,
        "counts": dict(item.counts),
        "findings": [review_finding_dict(f) for f in item.findings],
        "completedAt": _dt(item.completed_at),
    }


def board_column_dict(*, status: str, title: str, tasks: list[BidTaskEntity]) -> dict[str, Any]:
    return {
        "status": status,
        "title": title,
        "count": len(tasks),
        "tasks": [task_summary_dict(t) for t in tasks],
    }
