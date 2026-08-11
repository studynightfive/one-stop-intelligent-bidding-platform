"""评标域内存仓储：在 M4 DB 会话就绪前支撑契约测试与业务验证。"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

from app.domains.evaluations.entities import (
    EvaluationEntity,
    EvaluationReportEntity,
    MaterialCheckEntity,
    PortalActivityEntity,
    PortalDraftEntity,
    PortalSessionEntity,
    PriceRoundEntity,
    QuoteSubmissionEntity,
    RiskFindingEntity,
    ScoreItemEntity,
    SupplementNoticeEntity,
    SupplierSubmissionEntity,
)
from app.domains.evaluations.errors import not_found


class EvaluationStore:
    def __init__(self) -> None:
        self.evaluations: dict[str, EvaluationEntity] = {}
        self.submissions: dict[str, SupplierSubmissionEntity] = {}
        self.notices: dict[str, SupplementNoticeEntity] = {}
        self.rounds: dict[str, PriceRoundEntity] = {}
        self.quotes: dict[str, QuoteSubmissionEntity] = {}
        self.scores: dict[str, ScoreItemEntity] = {}
        self.risks: dict[str, RiskFindingEntity] = {}
        self.material_checks: dict[str, MaterialCheckEntity] = {}
        self.reports: dict[str, EvaluationReportEntity] = {}
        self.drafts: dict[str, PortalDraftEntity] = {}
        self.activities: list[PortalActivityEntity] = []
        self.sessions: dict[str, PortalSessionEntity] = {}
        self.invite_hash_index: dict[str, str] = {}  # hash -> supplier_id
        self.idempotency: dict[str, Any] = {}
        self.token_hash_index: dict[str, str] = {}  # access token_hash -> session_id
        self.refresh_hash_index: dict[str, str] = {}  # refresh token_hash -> session_id

        from app.domains.evaluations.demo_seed import seed_demo_evaluation_store

        seed_demo_evaluation_store(self)

    def save_evaluation(self, entity: EvaluationEntity) -> EvaluationEntity:
        self.evaluations[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def get_evaluation(self, evaluation_id: str, *, tenant_id: str) -> EvaluationEntity:
        entity = self.evaluations.get(evaluation_id)
        if entity is None or entity.tenant_id != tenant_id:
            raise not_found("评标任务不存在", evaluationId=evaluation_id)
        return copy.deepcopy(entity)

    def list_evaluations(
        self,
        *,
        tenant_id: str,
        keyword: str | None = None,
        status: str | None = None,
        assignee_id: str | None = None,
    ) -> list[EvaluationEntity]:
        items = [e for e in self.evaluations.values() if e.tenant_id == tenant_id]
        if status:
            items = [e for e in items if e.status == status]
        if assignee_id:
            items = [e for e in items if e.assignee_id == assignee_id]
        if keyword:
            q = keyword.lower()
            items = [
                e
                for e in items
                if q in e.project_name.lower() or q in e.tender_no.lower() or q in e.tender_entity.lower()
            ]
        items.sort(key=lambda e: e.updated_at, reverse=True)
        return [copy.deepcopy(e) for e in items]

    def risk_count(self, evaluation_id: str) -> int:
        return sum(1 for r in self.risks.values() if r.evaluation_id == evaluation_id and r.decision == "pending")

    def save_submission(self, entity: SupplierSubmissionEntity) -> SupplierSubmissionEntity:
        self.submissions[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def list_submissions(self, *, evaluation_id: str, supplier_id: str) -> list[SupplierSubmissionEntity]:
        return [
            copy.deepcopy(s)
            for s in self.submissions.values()
            if s.evaluation_id == evaluation_id and s.supplier_id == supplier_id
        ]

    def find_submission(self, *, supplier_id: str, material_id: str) -> SupplierSubmissionEntity | None:
        for item in self.submissions.values():
            if item.supplier_id == supplier_id and item.material_id == material_id:
                return copy.deepcopy(item)
        return None

    def save_notice(self, entity: SupplementNoticeEntity) -> SupplementNoticeEntity:
        self.notices[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def list_notices(self, *, evaluation_id: str, supplier_id: str | None = None) -> list[SupplementNoticeEntity]:
        items = [n for n in self.notices.values() if n.evaluation_id == evaluation_id]
        if supplier_id:
            items = [n for n in items if n.supplier_id == supplier_id]
        items.sort(key=lambda n: n.sent_at, reverse=True)
        return [copy.deepcopy(n) for n in items]

    def get_notice(self, notice_id: str) -> SupplementNoticeEntity:
        entity = self.notices.get(notice_id)
        if entity is None:
            raise not_found("补材料通知不存在", noticeId=notice_id)
        return copy.deepcopy(entity)

    def save_round(self, entity: PriceRoundEntity) -> PriceRoundEntity:
        self.rounds[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def get_round(self, round_id: str) -> PriceRoundEntity:
        entity = self.rounds.get(round_id)
        if entity is None:
            raise not_found("报价轮次不存在", roundId=round_id)
        return copy.deepcopy(entity)

    def list_rounds(self, *, evaluation_id: str) -> list[PriceRoundEntity]:
        items = [r for r in self.rounds.values() if r.evaluation_id == evaluation_id]
        items.sort(key=lambda r: r.round_number)
        return [copy.deepcopy(r) for r in items]

    def save_quote(self, entity: QuoteSubmissionEntity) -> QuoteSubmissionEntity:
        self.quotes[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def list_quotes(self, *, evaluation_id: str, round_id: str | None = None) -> list[QuoteSubmissionEntity]:
        items = [q for q in self.quotes.values() if q.evaluation_id == evaluation_id]
        if round_id:
            items = [q for q in items if q.round_id == round_id]
        return [copy.deepcopy(q) for q in items]

    def find_quote(self, *, round_id: str, supplier_id: str) -> QuoteSubmissionEntity | None:
        for item in self.quotes.values():
            if item.round_id == round_id and item.supplier_id == supplier_id:
                return copy.deepcopy(item)
        return None

    def find_quote_by_idempotency(
        self,
        *,
        evaluation_id: str,
        round_id: str,
        supplier_id: str,
        key: str,
    ) -> QuoteSubmissionEntity | None:
        for item in self.quotes.values():
            if (
                item.evaluation_id == evaluation_id
                and item.round_id == round_id
                and item.supplier_id == supplier_id
                and item.idempotency_key == key
            ):
                return copy.deepcopy(item)
        return None

    def score_key(self, evaluation_id: str, supplier_id: str, criterion_id: str) -> str:
        return f"{evaluation_id}:{supplier_id}:{criterion_id}"

    def save_score(self, entity: ScoreItemEntity) -> ScoreItemEntity:
        key = self.score_key(entity.evaluation_id, entity.supplier_id, entity.criterion_id)
        self.scores[key] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def list_scores(
        self, *, evaluation_id: str, supplier_id: str | None = None, category: str | None = None
    ) -> list[ScoreItemEntity]:
        _ = category
        items = [s for s in self.scores.values() if s.evaluation_id == evaluation_id]
        if supplier_id:
            items = [s for s in items if s.supplier_id == supplier_id]
        return [copy.deepcopy(s) for s in items]

    def get_score(self, evaluation_id: str, supplier_id: str, criterion_id: str) -> ScoreItemEntity:
        key = self.score_key(evaluation_id, supplier_id, criterion_id)
        entity = self.scores.get(key)
        if entity is None:
            raise not_found("评分项不存在")
        return copy.deepcopy(entity)

    def save_risk(self, entity: RiskFindingEntity) -> RiskFindingEntity:
        self.risks[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def list_risks(
        self,
        *,
        evaluation_id: str,
        severity: str | None = None,
        decision: str | None = None,
        supplier_id: str | None = None,
    ) -> list[RiskFindingEntity]:
        items = [r for r in self.risks.values() if r.evaluation_id == evaluation_id]
        if severity:
            items = [r for r in items if r.severity == severity]
        if decision:
            items = [r for r in items if r.decision == decision]
        if supplier_id:
            items = [r for r in items if r.supplier_id == supplier_id]
        return [copy.deepcopy(r) for r in items]

    def get_risk(self, risk_id: str) -> RiskFindingEntity:
        entity = self.risks.get(risk_id)
        if entity is None:
            raise not_found("风险项不存在", riskId=risk_id)
        return copy.deepcopy(entity)

    def save_material_check(self, entity: MaterialCheckEntity) -> MaterialCheckEntity:
        self.material_checks[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def latest_material_check(self, evaluation_id: str) -> MaterialCheckEntity | None:
        items = [m for m in self.material_checks.values() if m.evaluation_id == evaluation_id]
        if not items:
            return None
        items.sort(key=lambda m: m.completed_at or datetime.min, reverse=True)
        return copy.deepcopy(items[0])

    def save_report(self, entity: EvaluationReportEntity) -> EvaluationReportEntity:
        self.reports[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def list_reports(self, *, evaluation_id: str) -> list[EvaluationReportEntity]:
        items = [r for r in self.reports.values() if r.evaluation_id == evaluation_id]
        items.sort(key=lambda r: r.version_number, reverse=True)
        return [copy.deepcopy(r) for r in items]

    def get_report(self, report_id: str) -> EvaluationReportEntity:
        entity = self.reports.get(report_id)
        if entity is None:
            raise not_found("报告不存在", reportId=report_id)
        return copy.deepcopy(entity)

    def save_draft(self, entity: PortalDraftEntity) -> PortalDraftEntity:
        self.drafts[entity.supplier_id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def get_draft(self, supplier_id: str) -> PortalDraftEntity | None:
        entity = self.drafts.get(supplier_id)
        return copy.deepcopy(entity) if entity else None

    def add_activity(self, entity: PortalActivityEntity) -> PortalActivityEntity:
        self.activities.append(copy.deepcopy(entity))
        return copy.deepcopy(entity)

    def list_activities(self, *, evaluation_id: str, supplier_id: str) -> list[PortalActivityEntity]:
        items = [a for a in self.activities if a.evaluation_id == evaluation_id and a.supplier_id == supplier_id]
        items.sort(key=lambda a: a.occurred_at, reverse=True)
        return [copy.deepcopy(a) for a in items]

    def save_session(self, entity: PortalSessionEntity) -> PortalSessionEntity:
        self.sessions[entity.token_id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def get_session(self, token_id: str) -> PortalSessionEntity:
        entity = self.sessions.get(token_id)
        if entity is None or entity.revoked:
            raise not_found("门户会话不存在或已失效")
        return copy.deepcopy(entity)

    def remember_idempotency(self, key: str, value: Any) -> None:
        self.idempotency[key] = copy.deepcopy(value)

    def get_idempotency(self, key: str) -> Any | None:
        value = self.idempotency.get(key)
        return copy.deepcopy(value) if value is not None else None
