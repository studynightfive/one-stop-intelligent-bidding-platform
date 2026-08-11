"""多轮报价与价格比较（Decimal 金额）。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.domains.evaluations.access import require_owner, require_viewer
from app.domains.evaluations.entities import PriceRoundEntity, QuoteSubmissionEntity
from app.domains.evaluations.errors import conflict, deadline_passed, forbidden, validation_error
from app.domains.evaluations.ids import new_id
from app.domains.evaluations.mappers import quote_dict, round_dict
from app.domains.evaluations.money import format_money, parse_money
from app.domains.evaluations.ports import AuditEventInput, AuditServicePort, AuthPrincipal, PortalPrincipal
from app.domains.evaluations.state_machine import assert_supplier_transition
from app.domains.evaluations.store import EvaluationStore


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _unwrap(value: Any) -> Any:
    return getattr(value, "root", value)


class PricingService:
    def __init__(self, store: EvaluationStore, *, audit: AuditServicePort) -> None:
        self.store = store
        self.audit = audit

    async def create_round(self, actor: AuthPrincipal, evaluation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        if entity.status not in {"collecting", "pending", "ai_review", "human_review"}:
            raise conflict("当前状态不可发起报价轮次", currentStatus=entity.status)
        existing = self.store.list_rounds(evaluation_id=evaluation_id)
        if entity.review_settings.multi_round_pricing is False and existing:
            raise conflict("未启用多轮报价")
        if len(existing) >= entity.review_settings.max_rounds:
            raise conflict("已达到最大报价轮次")
        opens_at = _parse_dt(_unwrap(payload["opensAt"]))
        deadline = _parse_dt(_unwrap(payload["deadline"]))
        if opens_at >= deadline:
            raise validation_error("报价截止必须晚于开放时间")
        eligible = [str(_unwrap(i)) for i in payload["eligibleSupplierIds"]]
        supplier_ids = {s.id for s in entity.suppliers}
        if not set(eligible).issubset(supplier_ids):
            raise validation_error("存在无效的供应商 ID")
        now = _now()
        status = "scheduled" if opens_at > now else "open"
        round_entity = PriceRoundEntity(
            id=new_id(),
            evaluation_id=evaluation_id,
            round_number=len(existing) + 1,
            title=str(payload["title"]).strip(),
            opens_at=opens_at,
            deadline=deadline,
            status=status,
            eligible_supplier_ids=eligible,
            ranking_visible_to_supplier=bool(payload["rankingVisibleToSupplier"]),
        )
        saved = self.store.save_round(round_entity)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="evaluation",
                aggregate_id=evaluation_id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="price_round.created",
                summary=f"创建报价轮次 {saved.round_number}",
            )
        )
        return round_dict(saved, submission_count=0)

    async def list_rounds(self, actor: AuthPrincipal, evaluation_id: str) -> list[dict[str, Any]]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_viewer(actor, entity)
        result = []
        for item in self.store.list_rounds(evaluation_id=evaluation_id):
            count = len(self.store.list_quotes(evaluation_id=evaluation_id, round_id=item.id))
            result.append(round_dict(item, submission_count=count))
        return result

    async def close_round(self, actor: AuthPrincipal, evaluation_id: str, round_id: str) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        round_entity = self.store.get_round(round_id)
        if round_entity.evaluation_id != evaluation_id:
            raise conflict("轮次不属于该评标任务")
        if round_entity.status == "closed":
            raise conflict("轮次已关闭")
        round_entity.status = "closed"
        round_entity.version += 1
        saved = self.store.save_round(round_entity)
        count = len(self.store.list_quotes(evaluation_id=evaluation_id, round_id=round_id))
        return round_dict(saved, submission_count=count)

    async def comparison(self, actor: AuthPrincipal, evaluation_id: str) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_viewer(actor, entity)
        rounds = self.store.list_rounds(evaluation_id=evaluation_id)
        round_blocks = []
        supplier_points: dict[str, list[dict[str, Any]]] = {}
        for round_entity in rounds:
            quotes = self.store.list_quotes(evaluation_id=evaluation_id, round_id=round_entity.id)
            quotes_sorted = sorted(quotes, key=lambda q: q.amount)
            count = len(quotes)
            round_blocks.append(
                {
                    "round": round_dict(round_entity, submission_count=count),
                    "quotes": [quote_dict(q) for q in quotes],
                }
            )
            for rank, quote in enumerate(quotes_sorted, start=1):
                points = supplier_points.setdefault(quote.supplier_id, [])
                prev = points[-1]["amount"] if points else None
                decrease = None
                if prev is not None:
                    prev_amount = parse_money(prev)
                    if prev_amount > 0:
                        decrease = format_money((prev_amount - quote.amount) * Decimal("100") / prev_amount)
                points.append(
                    {
                        "roundNumber": round_entity.round_number,
                        "amount": format_money(quote.amount),
                        "decreasePercent": decrease,
                        "rank": rank,
                    }
                )
        return {
            "rounds": round_blocks,
            "supplierTrends": [{"supplierId": sid, "points": pts} for sid, pts in supplier_points.items()],
        }

    async def submit_quote(
        self,
        portal: PortalPrincipal,
        round_id: str,
        *,
        amount: str,
        currency: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        if idempotency_key:
            existing = self.store.find_quote_by_idempotency(
                evaluation_id=portal.evaluation_id,
                round_id=round_id,
                supplier_id=portal.supplier_id,
                key=idempotency_key,
            )
            if existing is not None:
                return quote_dict(existing)
        entity = self.store.get_evaluation(portal.evaluation_id, tenant_id=portal.tenant_id)
        if entity.status == "closed":
            raise conflict("评标已关闭")
        round_entity = self.store.get_round(round_id)
        if round_entity.evaluation_id != portal.evaluation_id:
            raise forbidden("无权访问该报价轮次")
        now = _now()
        if round_entity.status == "scheduled" and round_entity.opens_at > now:
            raise conflict("报价轮次尚未开放")
        if round_entity.status == "closed" or round_entity.deadline < now:
            raise deadline_passed("报价截止时间已过")
        if portal.supplier_id not in round_entity.eligible_supplier_ids:
            raise forbidden("当前供应商不在本轮资格名单")
        if currency != "CNY":
            raise validation_error("仅支持 CNY")
        money = parse_money(amount)
        prior = self.store.find_quote(round_id=round_id, supplier_id=portal.supplier_id)
        if prior is not None:
            raise conflict("本轮已提交报价，请勿重复提交")
        quote = QuoteSubmissionEntity(
            id=new_id(),
            round_id=round_id,
            evaluation_id=portal.evaluation_id,
            supplier_id=portal.supplier_id,
            amount=money,
            currency="CNY",
            submitted_at=now,
            idempotency_key=idempotency_key,
        )
        saved = self.store.save_quote(quote)
        for supplier in entity.suppliers:
            if supplier.id == portal.supplier_id:
                supplier.current_quote = money
                break
        entity.updated_at = now
        self.store.save_evaluation(entity)
        await self.audit.append(
            AuditEventInput(
                tenant_id=portal.tenant_id,
                aggregate_type="supplier",
                aggregate_id=portal.supplier_id,
                actor_type="supplier",
                actor_id=portal.supplier_id,
                actor_name=portal.name,
                action="quote.submitted",
                summary=f"提交第 {round_entity.round_number} 轮报价 {format_money(money)}",
            )
        )
        return quote_dict(saved)

    async def create_supplement_notice(
        self, actor: AuthPrincipal, evaluation_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        from datetime import timedelta

        from app.domains.evaluations.entities import SupplementNoticeEntity
        from app.domains.evaluations.mappers import notice_dict

        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        supplier_id = str(_unwrap(payload["supplierId"]))
        supplier = next((s for s in entity.suppliers if s.id == supplier_id), None)
        if supplier is None:
            raise validation_error("供应商不存在")
        material_ids = [str(_unwrap(i)) for i in payload["materialIds"]]
        known = {m.id for m in entity.materials}
        if not set(material_ids).issubset(known):
            raise validation_error("存在无效材料 ID")
        now = _now()
        if supplier.status == "submitted":
            assert_supplier_transition(supplier.status, "supplementing")
            supplier.status = "supplementing"
        notice = SupplementNoticeEntity(
            id=new_id(),
            evaluation_id=evaluation_id,
            supplier_id=supplier_id,
            material_ids=material_ids,
            message=str(payload["message"]).strip(),
            deadline=now + timedelta(minutes=int(payload["deadlineMinutes"])),
            status="sent",
            sent_at=now,
        )
        saved = self.store.save_notice(notice)
        entity.updated_at = now
        self.store.save_evaluation(entity)
        return notice_dict(saved)

    async def list_notices(
        self, actor: AuthPrincipal, evaluation_id: str, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        from app.domains.evaluations.mappers import notice_dict

        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_viewer(actor, entity)
        items = self.store.list_notices(evaluation_id=evaluation_id)
        total = len(items)
        start = (page - 1) * page_size
        data = [notice_dict(n) for n in items[start : start + page_size]]
        meta = {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size if page_size else 0,
        }
        return data, meta
