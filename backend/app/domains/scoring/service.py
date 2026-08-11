"""评分、风险、排名与报告元数据编排。"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any, cast

from app.domains.documents.generator import build_bid_docx
from app.domains.evaluations.access import require_owner, require_reviewer, require_viewer
from app.domains.evaluations.entities import (
    EvaluationReportEntity,
    MaterialCheckEntity,
    RiskFindingEntity,
    ScoreItemEntity,
)
from app.domains.evaluations.errors import conflict, not_found, validation_error, version_conflict
from app.domains.evaluations.ids import new_id
from app.domains.evaluations.mappers import report_dict, risk_dict, score_dict
from app.domains.evaluations.money import format_score, parse_score, weighted_score
from app.domains.evaluations.pdf_util import build_simple_pdf
from app.domains.evaluations.ports import (
    AuditEventInput,
    AuditServicePort,
    AuthPrincipal,
    FileRefSnapshot,
    FileServicePort,
    JobDispatcherPort,
    JobRefSnapshot,
)
from app.domains.evaluations.state_machine import (
    assert_evaluation_transition,
    evaluation_progress_for,
    evaluation_step_for,
)
from app.domains.evaluations.store import EvaluationStore


def _now() -> datetime:
    return datetime.now(UTC)


def _unwrap(value: Any) -> Any:
    return getattr(value, "root", value)


def _job_ref_dict(job: JobRefSnapshot) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "progressPercent": job.progress_percent,
        "createdAt": job.created_at.isoformat().replace("+00:00", "Z"),
        "currentStep": job.current_step,
    }
    if job.result is not None:
        data["result"] = job.result
    if job.error is not None:
        data["error"] = job.error
    return data


def _worker_output(job: JobRefSnapshot) -> dict[str, Any] | None:
    if job.status != "succeeded" or not isinstance(job.result, Mapping):
        return None
    output = job.result.get("output")
    return dict(output) if isinstance(output, Mapping) else None


def _confidence(value: Any, *, default: float = 0.75) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _safe_file_stem(value: str) -> str:
    stem = re.sub(r'[\\/:*?"<>|]+', "-", value).strip(" .-")
    return stem[:80] or "evaluation-report"


class ScoringService:
    def __init__(
        self,
        store: EvaluationStore,
        *,
        jobs: JobDispatcherPort,
        audit: AuditServicePort,
        files: FileServicePort,
    ) -> None:
        self.store = store
        self.jobs = jobs
        self.audit = audit
        self.files = files

    async def start_material_check(self, actor: AuthPrincipal, evaluation_id: str) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_reviewer(actor, entity)
        submission_summary = []
        for supplier in entity.suppliers:
            supplier_submissions = self.store.list_submissions(evaluation_id=evaluation_id, supplier_id=supplier.id)
            submission_summary.append(
                {
                    "supplierId": supplier.id,
                    "supplierName": supplier.name,
                    "materialIds": [item.material_id for item in supplier_submissions if item.status != "replaced"],
                }
            )
        job = await self.jobs.enqueue(
            tenant_id=actor.tenant_id,
            job_type="evaluation.material_check",
            payload={
                "evaluationId": evaluation_id,
                "requiredMaterials": [
                    {"id": item.id, "name": item.name, "required": item.required} for item in entity.materials
                ],
                "submissions": submission_summary,
            },
            created_by=actor.user_id,
        )
        output = _worker_output(job)
        rows: list[dict[str, Any]] = []
        if output is not None:
            missing_hints = [str(item).casefold() for item in output.get("missing", []) if str(item).strip()]
            completeness = _confidence(output.get("completeness"), default=0.8)
            for supplier in entity.suppliers:
                submitted_material_ids = {
                    item.material_id
                    for item in self.store.list_submissions(evaluation_id=evaluation_id, supplier_id=supplier.id)
                    if item.status != "replaced"
                }
                for index, material in enumerate(sorted(entity.materials, key=lambda item: item.sort_order)):
                    inferred_provided = (
                        material.id in submitted_material_ids or index < supplier.submitted_material_count
                    )
                    hinted_missing = any(
                        hint in material.name.casefold() or material.name.casefold() in hint for hint in missing_hints
                    )
                    provided = inferred_provided and not hinted_missing
                    rows.append(
                        {
                            "supplierId": supplier.id,
                            "materialId": material.id,
                            "result": "provided" if provided else "missing",
                            "evidence": [
                                "已绑定供应商提交文件"
                                if material.id in submitted_material_ids
                                else "根据供应商提交计数与 AI 完整性结果核验",
                            ],
                            "confidence": completeness,
                        }
                    )
        check = MaterialCheckEntity(
            id=new_id(),
            evaluation_id=evaluation_id,
            status="succeeded" if output is not None else "queued",
            rows=rows,
            completed_at=_now() if output is not None else None,
        )
        self.store.save_material_check(check)
        return _job_ref_dict(job)

    async def latest_material_check(self, actor: AuthPrincipal, evaluation_id: str) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_viewer(actor, entity)
        latest = self.store.latest_material_check(evaluation_id)
        if latest is None:
            raise not_found("尚无材料检查结果")
        data: dict[str, Any] = {
            "id": latest.id,
            "evaluationId": latest.evaluation_id,
            "status": latest.status,
            "rows": latest.rows,
        }
        if latest.completed_at:
            data["completedAt"] = latest.completed_at.isoformat().replace("+00:00", "Z")
        return data

    async def start_risk_check(self, actor: AuthPrincipal, evaluation_id: str) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_reviewer(actor, entity)
        rounds = self.store.list_rounds(evaluation_id=evaluation_id)
        job = await self.jobs.enqueue(
            tenant_id=actor.tenant_id,
            job_type="evaluation.risk_check",
            payload={
                "evaluationId": evaluation_id,
                "suppliers": [
                    {
                        "id": supplier.id,
                        "name": supplier.name,
                        "status": supplier.status,
                        "currentQuote": str(supplier.current_quote) if supplier.current_quote is not None else None,
                    }
                    for supplier in entity.suppliers
                ],
                "history": [
                    {
                        "roundId": price_round.id,
                        "roundNumber": price_round.round_number,
                        "quotes": [
                            {"supplierId": quote.supplier_id, "amount": str(quote.amount)}
                            for quote in self.store.list_quotes(
                                evaluation_id=evaluation_id,
                                round_id=price_round.id,
                            )
                        ],
                    }
                    for price_round in rounds
                ],
            },
            created_by=actor.user_id,
        )
        output = _worker_output(job)
        findings = output.get("findings") if output is not None else None
        if isinstance(findings, list) and entity.suppliers:
            supplier_ids = {supplier.id for supplier in entity.suppliers}
            for index, raw in enumerate(findings):
                if not isinstance(raw, Mapping):
                    continue
                supplier_id = str(raw.get("supplierId") or "")
                if supplier_id not in supplier_ids:
                    supplier_id = entity.suppliers[index % len(entity.suppliers)].id
                severity = str(raw.get("severity") or "warning").lower()
                if severity not in {"info", "warning", "high", "critical"}:
                    severity = "warning"
                evidence = raw.get("evidence")
                if not isinstance(evidence, list):
                    evidence = [str(evidence)] if evidence else ["AI 风险识别结果"]
                self.store.save_risk(
                    RiskFindingEntity(
                        id=new_id(),
                        evaluation_id=evaluation_id,
                        supplier_id=supplier_id,
                        type=str(raw.get("type") or "evaluation_risk"),
                        severity=severity,
                        title=str(raw.get("title") or raw.get("type") or "AI 识别风险"),
                        evidence=[str(item) for item in evidence if str(item).strip()],
                        decision="pending",
                        ai_confidence=_confidence(raw.get("confidence")),
                    )
                )
        # 异步队列模式保留可见占位项，等待外部 Worker 回写。
        if output is None and not self.store.list_risks(evaluation_id=evaluation_id):
            for supplier in entity.suppliers:
                self.store.save_risk(
                    RiskFindingEntity(
                        id=new_id(),
                        evaluation_id=evaluation_id,
                        supplier_id=supplier.id,
                        type="disqualification_risk",
                        severity="warning",
                        title="AI 建议待人工确认的废标风险",
                        evidence=["等待 Worker 回写证据"],
                        decision="pending",
                        ai_confidence=0.5,
                    )
                )
        return _job_ref_dict(job)

    async def list_risks(
        self,
        actor: AuthPrincipal,
        evaluation_id: str,
        *,
        severity: str | None = None,
        decision: str | None = None,
        supplier_id: str | None = None,
    ) -> list[dict[str, Any]]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_viewer(actor, entity)
        items = self.store.list_risks(
            evaluation_id=evaluation_id, severity=severity, decision=decision, supplier_id=supplier_id
        )
        return [risk_dict(i) for i in items]

    async def decide_risk(
        self, actor: AuthPrincipal, evaluation_id: str, risk_id: str, *, decision: str, reason: str
    ) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_reviewer(actor, entity)
        risk = self.store.get_risk(risk_id)
        if risk.evaluation_id != evaluation_id:
            raise not_found("风险项不存在")
        if decision not in {"passed", "rejected"}:
            raise validation_error("decision 仅支持 passed/rejected")
        if not reason.strip():
            raise validation_error("人工决定必须填写原因")
        risk.decision = decision
        risk.decision_reason = reason.strip()
        risk.decided_by_id = actor.user_id
        risk.decided_by_name = actor.name
        risk.decided_at = _now()
        risk.version += 1
        saved = self.store.save_risk(risk)
        if decision == "rejected":
            for supplier in entity.suppliers:
                if supplier.id == risk.supplier_id and supplier.status in {"submitted", "supplementing", "partial"}:
                    supplier.status = "disqualified"
            self.store.save_evaluation(entity)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="evaluation",
                aggregate_id=evaluation_id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="risk.decided",
                summary=f"风险人工决定={decision}",
                target_type="risk",
                target_id=risk_id,
                changes=({"field": "decision", "oldValue": "pending", "newValue": decision},),
            )
        )
        return risk_dict(saved)

    async def start_ai_scoring(self, actor: AuthPrincipal, evaluation_id: str) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_reviewer(actor, entity)
        if entity.status not in {"collecting", "pending"}:
            raise conflict("当前状态不可发起 AI 评分", currentStatus=entity.status)
        if entity.status == "collecting":
            assert_evaluation_transition("collecting", "pending")
            entity.status = "pending"
        assert_evaluation_transition("pending", "ai_review")
        entity.status = "ai_review"
        entity.current_step = evaluation_step_for("ai_review")
        entity.progress_percent = evaluation_progress_for("ai_review")
        entity.updated_at = _now()
        self.store.save_evaluation(entity)
        job = await self.jobs.enqueue(
            tenant_id=actor.tenant_id,
            job_type="evaluation.ai_scoring",
            payload={
                "evaluationId": evaluation_id,
                "scoringCriteria": [
                    {
                        "id": criterion.id,
                        "name": criterion.name,
                        "category": criterion.category,
                        "maxScore": str(criterion.max_score),
                        "weightPercent": str(criterion.weight_percent),
                        "description": criterion.description,
                    }
                    for criterion in entity.criteria
                ],
                "supplierResponse": [
                    {
                        "id": supplier.id,
                        "name": supplier.name,
                        "status": supplier.status,
                        "submittedMaterialCount": supplier.submitted_material_count,
                        "requiredMaterialCount": supplier.required_material_count,
                        "currentQuote": str(supplier.current_quote) if supplier.current_quote is not None else None,
                    }
                    for supplier in entity.suppliers
                ],
            },
            created_by=actor.user_id,
        )
        output = _worker_output(job)
        raw_scores = output.get("scores") if output is not None else None
        ai_scores = (
            [dict(item) for item in raw_scores if isinstance(item, Mapping)] if isinstance(raw_scores, list) else []
        )
        for supplier in entity.suppliers:
            if supplier.status == "disqualified":
                continue
            for criterion in entity.criteria:
                key_exists = False
                try:
                    self.store.get_score(evaluation_id, supplier.id, criterion.id)
                    key_exists = True
                except Exception:
                    key_exists = False
                if key_exists:
                    continue
                matched = next(
                    (
                        item
                        for item in ai_scores
                        if str(item.get("criterionName") or "").casefold() in criterion.name.casefold()
                        or criterion.name.casefold() in str(item.get("criterionName") or "").casefold()
                    ),
                    None,
                )
                try:
                    ai = Decimal(str(matched.get("score"))).quantize(Decimal("0.01")) if matched is not None else None
                except (InvalidOperation, TypeError, ValueError):
                    ai = None
                if ai is None:
                    ai = (criterion.max_score * Decimal("0.70")).quantize(Decimal("0.01"))
                ai = min(max(ai, Decimal("0")), criterion.max_score)
                basis = (
                    str(matched.get("basis") or "AI 建议，待人工确认") if matched is not None else "AI 建议，待人工确认"
                )
                self.store.save_score(
                    ScoreItemEntity(
                        evaluation_id=evaluation_id,
                        supplier_id=supplier.id,
                        criterion_id=criterion.id,
                        ai_score=ai,
                        ai_basis=basis,
                        final_score=ai,
                    )
                )
        return _job_ref_dict(job)

    async def list_scores(
        self, actor: AuthPrincipal, evaluation_id: str, *, supplier_id: str | None = None, category: str | None = None
    ) -> list[dict[str, Any]]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_viewer(actor, entity)
        criteria_by_id = {c.id: c for c in entity.criteria}
        items = self.store.list_scores(evaluation_id=evaluation_id, supplier_id=supplier_id)
        if category:
            items = [
                i
                for i in items
                if criteria_by_id.get(i.criterion_id) and criteria_by_id[i.criterion_id].category == category
            ]
        return [score_dict(i) for i in items]

    async def adjust_score(
        self,
        actor: AuthPrincipal,
        evaluation_id: str,
        supplier_id: str,
        criterion_id: str,
        *,
        human_score: str,
        adjustment_reason: str,
        if_match: int | None,
    ) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_reviewer(actor, entity)
        if entity.status not in {"ai_review", "human_review"}:
            raise conflict("当前状态不可人工改分", currentStatus=entity.status)
        if not adjustment_reason.strip():
            raise validation_error("人工调分必须填写原因")
        score = self.store.get_score(evaluation_id, supplier_id, criterion_id)
        if if_match is not None and if_match != score.version:
            raise version_conflict(score.version)
        criterion = next((c for c in entity.criteria if c.id == criterion_id), None)
        if criterion is None:
            raise not_found("评分标准不存在")
        human = parse_score(human_score)
        if human < 0 or human > criterion.max_score:
            raise validation_error("人工分超出评分标准上限")
        old = format_score(score.final_score)
        score.human_score = human
        score.adjustment_reason = adjustment_reason.strip()
        score.final_score = human
        score.adjusted_by_id = actor.user_id
        score.adjusted_by_name = actor.name
        score.adjusted_at = _now()
        score.version += 1
        if entity.status == "ai_review":
            assert_evaluation_transition("ai_review", "human_review")
            entity.status = "human_review"
            entity.current_step = evaluation_step_for("human_review")
            entity.progress_percent = evaluation_progress_for("human_review")
            entity.updated_at = _now()
            self.store.save_evaluation(entity)
        saved = self.store.save_score(score)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="evaluation",
                aggregate_id=evaluation_id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="score.adjusted",
                summary="人工调整评分",
                changes=(
                    {"field": "finalScore", "oldValue": old, "newValue": format_score(human)},
                    {"field": "adjustmentReason", "oldValue": None, "newValue": adjustment_reason.strip()},
                ),
            )
        )
        return score_dict(saved)

    async def confirm_scores(
        self, actor: AuthPrincipal, evaluation_id: str, *, supplier_id: str | None, comment: str | None
    ) -> dict[str, bool]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_reviewer(actor, entity)
        items = self.store.list_scores(evaluation_id=evaluation_id, supplier_id=supplier_id)
        if not items:
            raise conflict("尚无评分可确认")
        for item in items:
            item.confirmed = True
            item.version += 1
            self.store.save_score(item)
        if entity.status == "human_review":
            assert_evaluation_transition("human_review", "completed")
            entity.status = "completed"
            entity.current_step = evaluation_step_for("completed")
            entity.progress_percent = evaluation_progress_for("completed")
            entity.updated_at = _now()
            self.store.save_evaluation(entity)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="evaluation",
                aggregate_id=evaluation_id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="scores.confirmed",
                summary=comment or "确认评分",
            )
        )
        return {"confirmed": True}

    async def ranking(self, actor: AuthPrincipal, evaluation_id: str) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_viewer(actor, entity)
        criteria = {c.id: c for c in entity.criteria}
        rows: list[dict[str, Any]] = []
        for supplier in entity.suppliers:
            if supplier.status == "withdrawn":
                continue
            scores = self.store.list_scores(evaluation_id=evaluation_id, supplier_id=supplier.id)
            buckets = {
                "qualification": Decimal("0"),
                "technical": Decimal("0"),
                "commercial": Decimal("0"),
                "service": Decimal("0"),
            }
            total = Decimal("0.00")
            for item in scores:
                criterion = criteria.get(item.criterion_id)
                if criterion is None:
                    continue
                part = weighted_score(item.final_score, criterion.weight_percent)
                buckets[criterion.category] = buckets.get(criterion.category, Decimal("0")) + part
                total += part
            rows.append(
                {
                    "supplierId": supplier.id,
                    "supplierName": supplier.name,
                    "qualificationScore": format_score(buckets.get("qualification", Decimal("0"))),
                    "technicalScore": format_score(buckets.get("technical", Decimal("0"))),
                    "commercialScore": format_score(buckets.get("commercial", Decimal("0"))),
                    "totalScore": format_score(total),
                    "status": supplier.status,
                    "_sort": total,
                }
            )
        rows.sort(key=lambda row: cast(Decimal, row["_sort"]), reverse=True)
        for idx, row in enumerate(rows, start=1):
            row["rank"] = idx
            row.pop("_sort", None)
        recommended = rows[0]["supplierId"] if rows else None
        return {
            "rows": rows,
            "recommendedSupplierId": recommended,
            "generatedAt": _now().isoformat().replace("+00:00", "Z"),
            "version": entity.version,
        }

    async def start_report(self, actor: AuthPrincipal, evaluation_id: str, formats: list[str]) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_reviewer(actor, entity)
        if entity.status not in {"human_review", "completed"}:
            raise conflict("当前状态不可生成评标报告", currentStatus=entity.status)
        normalized_formats = list(dict.fromkeys(str(item).lower() for item in formats))
        if not normalized_formats or any(item not in {"docx", "pdf"} for item in normalized_formats):
            raise validation_error("报告格式仅支持 docx/pdf")
        ranking = await self.ranking(actor, evaluation_id)
        risks = [risk_dict(item) for item in self.store.list_risks(evaluation_id=evaluation_id)]
        job = await self.jobs.enqueue(
            tenant_id=actor.tenant_id,
            job_type="evaluation.report_generate",
            payload={
                "evaluationId": evaluation_id,
                "projectName": entity.project_name,
                "ranking": ranking,
                "risks": risks,
                "formats": normalized_formats,
            },
            created_by=actor.user_id,
        )
        output = _worker_output(job)
        if output is not None:
            title = str(output.get("reportTitle") or f"{entity.project_name}评标报告")
            raw_sections = output.get("sections")
            sections: list[dict[str, Any]] = []
            if isinstance(raw_sections, list):
                for index, raw in enumerate(raw_sections, start=1):
                    if not isinstance(raw, Mapping):
                        continue
                    heading = str(raw.get("heading") or f"第 {index} 章")
                    body = str(raw.get("body") or "本章节暂无生成内容，请人工复核补充。")
                    sections.append({"heading": heading, "paragraphs": [{"index": 1, "text": body}]})
            if not sections:
                sections = [
                    {
                        "heading": "评审结论",
                        "paragraphs": [{"index": 1, "text": "评标结果已经系统汇总，请评审负责人复核。"}],
                    }
                ]
            for report_format in normalized_formats:
                if report_format == "docx":
                    content = build_bid_docx(
                        title=title,
                        template_name="标准评标报告模板",
                        sections=sections,
                    ).content
                    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                else:
                    lines = [title]
                    for section in sections:
                        lines.append(str(section["heading"]))
                        lines.extend(str(item["text"]) for item in section["paragraphs"])
                    content = build_simple_pdf(lines)
                    mime_type = "application/pdf"
                existing = [
                    item
                    for item in self.store.list_reports(evaluation_id=evaluation_id)
                    if item.format == report_format
                ]
                file_id = new_id()
                report = EvaluationReportEntity(
                    id=new_id(),
                    evaluation_id=evaluation_id,
                    format=report_format,
                    version_number=max((item.version_number for item in existing), default=0) + 1,
                    file_id=file_id,
                    created_by_id=actor.user_id,
                    created_by_name=actor.name,
                    created_at=_now(),
                    file_name=f"{_safe_file_stem(entity.project_name)}-评标报告.{report_format}",
                    mime_type=mime_type,
                    size_bytes=len(content),
                    sha256=sha256(content).hexdigest(),
                    content=content,
                )
                self.store.save_report(report)
        return _job_ref_dict(job)

    async def list_reports(self, actor: AuthPrincipal, evaluation_id: str) -> list[dict[str, Any]]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_viewer(actor, entity)
        result = []
        for report in self.store.list_reports(evaluation_id=evaluation_id):
            if report.content is not None:
                file = FileRefSnapshot(
                    id=report.file_id,
                    file_name=report.file_name or f"evaluation-report.{report.format}",
                    mime_type=report.mime_type or "application/octet-stream",
                    size_bytes=report.size_bytes or len(report.content),
                    sha256=report.sha256 or sha256(report.content).hexdigest(),
                    scan_status="clean",
                    created_at=report.created_at,
                )
            else:
                file = await self.files.get_file(tenant_id=actor.tenant_id, file_id=report.file_id)
            result.append(report_dict(report, file))
        return result

    async def apply_job_result_report(
        self, *, tenant_id: str, evaluation_id: str, format: str, file_id: str, actor_id: str, actor_name: str
    ) -> EvaluationReportEntity:
        """供 M7 JobResult 回写后由领域服务落库。"""
        existing = self.store.list_reports(evaluation_id=evaluation_id)
        version = (existing[0].version_number + 1) if existing else 1
        report = EvaluationReportEntity(
            id=new_id(),
            evaluation_id=evaluation_id,
            format=format,
            version_number=version,
            file_id=file_id,
            created_by_id=actor_id,
            created_by_name=actor_name,
            created_at=_now(),
        )
        _ = tenant_id
        return self.store.save_report(report)

    async def advance_to_pending(self, actor: AuthPrincipal, evaluation_id: str) -> dict[str, Any]:
        """收集期结束后进入 pending（内部动作，供测试/定时推进）。"""
        from app.domains.evaluations.mappers import evaluation_dict

        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        assert_evaluation_transition(entity.status, "pending")
        entity.status = "pending"
        entity.current_step = evaluation_step_for("pending")
        entity.progress_percent = evaluation_progress_for("pending")
        entity.updated_at = _now()
        saved = self.store.save_evaluation(entity)
        return evaluation_dict(saved, store=self.store)
