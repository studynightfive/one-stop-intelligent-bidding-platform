"""领域实体 -> 契约 camelCase 字典（不手写第二套 DTO 类）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.domains.evaluations.entities import (
    EvaluationEntity,
    EvaluationMaterialEntity,
    EvaluationReportEntity,
    PriceRoundEntity,
    QuoteSubmissionEntity,
    RiskFindingEntity,
    ScoreItemEntity,
    ScoringCriterionEntity,
    SupplementNoticeEntity,
    SupplierEntity,
    SupplierSubmissionEntity,
)
from app.domains.evaluations.money import format_money, format_score
from app.domains.evaluations.ports import FileRefSnapshot, JobRefSnapshot
from app.domains.evaluations.state_machine import EVALUATION_ACTIONS
from app.domains.evaluations.store import EvaluationStore


def _dt(value: datetime) -> str:
    if value.tzinfo is None:
        return value.isoformat() + "Z"
    return value.astimezone().isoformat().replace("+00:00", "Z")


def file_ref_dict(file: FileRefSnapshot) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": file.id,
        "fileName": file.file_name,
        "mimeType": file.mime_type,
        "sizeBytes": file.size_bytes,
        "sha256": file.sha256,
        "scanStatus": file.scan_status,
        "createdAt": _dt(file.created_at),
    }
    if file.preview_url:
        data["previewUrl"] = file.preview_url
    if file.download_url:
        data["downloadUrl"] = file.download_url
    return data


def job_ref_dict(job: JobRefSnapshot) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "progressPercent": job.progress_percent,
        "createdAt": _dt(job.created_at),
    }
    if job.current_step:
        data["currentStep"] = job.current_step
    return data


def material_dict(item: EvaluationMaterialEntity) -> dict[str, Any]:
    return {
        "id": item.id,
        "evaluationId": item.evaluation_id,
        "name": item.name,
        "category": item.category,
        "required": item.required,
        "allowedMimeTypes": list(item.allowed_mime_types),
        "maxSizeBytes": item.max_size_bytes,
        "sortOrder": item.sort_order,
    }


def criterion_dict(item: ScoringCriterionEntity) -> dict[str, Any]:
    data = {
        "id": item.id,
        "evaluationId": item.evaluation_id,
        "name": item.name,
        "category": item.category,
        "maxScore": format_score(item.max_score),
        "weightPercent": format_score(item.weight_percent),
        "method": item.method,
        "description": item.description,
        "sortOrder": item.sort_order,
    }
    if item.formula:
        data["formula"] = item.formula
    return data


def supplier_dict(item: SupplierEntity) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": item.id,
        "evaluationId": item.evaluation_id,
        "name": item.name,
        "contactName": item.contact_name,
        "email": item.email,
        "status": item.status,
        "submittedMaterialCount": item.submitted_material_count,
        "requiredMaterialCount": item.required_material_count,
    }
    if item.phone:
        data["phone"] = item.phone
    if item.current_quote is not None:
        data["currentQuote"] = format_money(item.current_quote)
    if item.submitted_at:
        data["submittedAt"] = _dt(item.submitted_at)
    return data


def review_settings_dict(entity: EvaluationEntity) -> dict[str, Any]:
    s = entity.review_settings
    return {
        "multiRoundPricing": s.multi_round_pricing,
        "maxRounds": s.max_rounds,
        "supplementDeadlineMinutes": s.supplement_deadline_minutes,
        "allowModifyBeforeDeadline": s.allow_modify_before_deadline,
        "notifyOnMissing": s.notify_on_missing,
        "closeSubmissionAtDeadline": s.close_submission_at_deadline,
    }


def evaluation_dict(entity: EvaluationEntity, *, store: EvaluationStore | None = None) -> dict[str, Any]:
    risk_count = store.risk_count(entity.id) if store else 0
    data: dict[str, Any] = {
        "id": entity.id,
        "projectName": entity.project_name,
        "tenderNo": entity.tender_no,
        "tenderEntity": entity.tender_entity,
        "budgetAmount": format_money(entity.budget_amount),
        "currency": entity.currency,
        "supplierDeadline": _dt(entity.supplier_deadline),
        "evaluationStartAt": _dt(entity.evaluation_start_at),
        "evaluationEndAt": _dt(entity.evaluation_end_at),
        "status": entity.status,
        "currentStep": entity.current_step,
        "progressPercent": entity.progress_percent,
        "assignee": {"id": entity.assignee_id, "name": entity.assignee_name},
        "supplierCount": entity.supplier_count,
        "riskCount": risk_count,
        "version": entity.version,
        "createdAt": _dt(entity.created_at),
        "updatedAt": _dt(entity.updated_at),
    }
    if entity.source_bid_task_id:
        data["sourceBidTaskId"] = entity.source_bid_task_id
    return data


def evaluation_detail_dict(
    entity: EvaluationEntity,
    *,
    store: EvaluationStore,
    jobs: list[JobRefSnapshot] | None = None,
) -> dict[str, Any]:
    data = evaluation_dict(entity, store=store)
    data.update(
        {
            "materials": [material_dict(m) for m in sorted(entity.materials, key=lambda x: x.sort_order)],
            "scoringCriteria": [criterion_dict(c) for c in sorted(entity.criteria, key=lambda x: x.sort_order)],
            "reviewSettings": review_settings_dict(entity),
            "reviewers": [
                {"id": rid, "name": entity.reviewer_names.get(rid, rid)} for rid in entity.reviewer_ids
            ],
            "suppliers": [supplier_dict(s) for s in entity.suppliers],
            "latestJobs": [job_ref_dict(j) for j in (jobs or [])],
            "allowedActions": EVALUATION_ACTIONS.get(entity.status, []),
        }
    )
    if entity.description:
        data["description"] = entity.description
    return data


def score_dict(item: ScoreItemEntity) -> dict[str, Any]:
    data: dict[str, Any] = {
        "supplierId": item.supplier_id,
        "criterionId": item.criterion_id,
        "finalScore": format_score(item.final_score),
        "version": item.version,
    }
    if item.ai_score is not None:
        data["aiScore"] = format_score(item.ai_score)
    if item.ai_basis:
        data["aiBasis"] = item.ai_basis
    if item.human_score is not None:
        data["humanScore"] = format_score(item.human_score)
    if item.adjustment_reason:
        data["adjustmentReason"] = item.adjustment_reason
    if item.adjusted_by_id and item.adjusted_by_name:
        data["adjustedBy"] = {"id": item.adjusted_by_id, "name": item.adjusted_by_name}
    if item.adjusted_at:
        data["adjustedAt"] = _dt(item.adjusted_at)
    return data


def risk_dict(item: RiskFindingEntity) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": item.id,
        "evaluationId": item.evaluation_id,
        "supplierId": item.supplier_id,
        "type": item.type,
        "severity": item.severity,
        "title": item.title,
        "evidence": list(item.evidence),
        "decision": item.decision,
        "version": item.version,
    }
    if item.ai_confidence is not None:
        data["aiConfidence"] = item.ai_confidence
    if item.decision_reason:
        data["decisionReason"] = item.decision_reason
    if item.decided_by_id and item.decided_by_name:
        data["decidedBy"] = {"id": item.decided_by_id, "name": item.decided_by_name}
    if item.decided_at:
        data["decidedAt"] = _dt(item.decided_at)
    return data


def round_dict(item: PriceRoundEntity, *, submission_count: int) -> dict[str, Any]:
    return {
        "id": item.id,
        "evaluationId": item.evaluation_id,
        "roundNumber": item.round_number,
        "title": item.title,
        "opensAt": _dt(item.opens_at),
        "deadline": _dt(item.deadline),
        "status": item.status,
        "eligibleSupplierIds": list(item.eligible_supplier_ids),
        "submissionCount": submission_count,
        "version": item.version,
    }


def quote_dict(item: QuoteSubmissionEntity) -> dict[str, Any]:
    return {
        "id": item.id,
        "roundId": item.round_id,
        "supplierId": item.supplier_id,
        "amount": format_money(item.amount),
        "currency": item.currency,
        "submittedAt": _dt(item.submitted_at),
        "version": item.version,
    }


def notice_dict(item: SupplementNoticeEntity) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": item.id,
        "evaluationId": item.evaluation_id,
        "supplierId": item.supplier_id,
        "materialIds": list(item.material_ids),
        "message": item.message,
        "deadline": _dt(item.deadline),
        "status": item.status,
        "sentAt": _dt(item.sent_at),
    }
    if item.responded_at:
        data["respondedAt"] = _dt(item.responded_at)
    return data


def submission_dict(item: SupplierSubmissionEntity, file: FileRefSnapshot) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": item.id,
        "supplierId": item.supplier_id,
        "materialId": item.material_id,
        "file": file_ref_dict(file),
        "status": item.status,
        "version": item.version,
    }
    if item.submitted_at:
        data["submittedAt"] = _dt(item.submitted_at)
    if item.replaced_at:
        data["replacedAt"] = _dt(item.replaced_at)
    return data


def report_dict(item: EvaluationReportEntity, file: FileRefSnapshot) -> dict[str, Any]:
    return {
        "id": item.id,
        "evaluationId": item.evaluation_id,
        "format": item.format,
        "versionNumber": item.version_number,
        "file": file_ref_dict(file),
        "createdBy": {"id": item.created_by_id, "name": item.created_by_name},
        "createdAt": _dt(item.created_at),
    }
