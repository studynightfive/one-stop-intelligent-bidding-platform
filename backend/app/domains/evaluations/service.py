"""评标任务服务：CRUD、配置、校验、发布、取消、关闭。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from app.domains.evaluations.access import (
    require_create,
    require_owner,
    require_viewer,
)
from app.domains.evaluations.entities import (
    EvaluationEntity,
    EvaluationMaterialEntity,
    ReviewSettingsEntity,
    ScoringCriterionEntity,
    SupplierEntity,
)
from app.domains.evaluations.errors import (
    conflict,
    deadline_passed,
    not_found,
    validation_error,
    version_conflict,
)
from app.domains.evaluations.ids import new_id
from app.domains.evaluations.mappers import (
    criterion_dict,
    evaluation_detail_dict,
    evaluation_dict,
    material_dict,
    review_settings_dict,
    supplier_dict,
)
from app.domains.evaluations.money import parse_money, parse_score, parse_weight
from app.domains.evaluations.ports import (
    AuditEventInput,
    AuditEventSnapshot,
    AuditServicePort,
    AuthPrincipal,
    BidTaskSnapshotPort,
    JobDispatcherPort,
    JobRefSnapshot,
    NotificationInput,
    NotificationServicePort,
)
from app.domains.evaluations.state_machine import (
    assert_evaluation_transition,
    evaluation_progress_for,
    evaluation_step_for,
)
from app.domains.evaluations.store import EvaluationStore
from app.domains.evaluations.validation import validate_evaluation
from app.domains.portal.security import default_invite_expiry, generate_invite_code


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _audit_event_dict(event: AuditEventSnapshot) -> dict[str, Any]:
    return {
        "id": event.id,
        "tenantId": event.tenant_id,
        "aggregateType": event.aggregate_type,
        "aggregateId": event.aggregate_id,
        "actorType": event.actor_type,
        "actorId": event.actor_id,
        "actorName": event.actor_name,
        "action": event.action,
        "targetType": event.target_type,
        "targetId": event.target_id,
        "summary": event.summary,
        "changes": list(event.changes) or None,
        "requestId": event.request_id,
        "ipAddress": event.ip_address,
        "createdAt": event.created_at.isoformat().replace("+00:00", "Z"),
    }


class EvaluationService:
    def __init__(
        self,
        store: EvaluationStore,
        *,
        bid_snapshot: BidTaskSnapshotPort,
        jobs: JobDispatcherPort,
        notifications: NotificationServicePort,
        audit: AuditServicePort,
        portal_base_url: str = "http://127.0.0.1:3210/evaluation/portal",
    ) -> None:
        self.store = store
        self.bid_snapshot = bid_snapshot
        self.jobs = jobs
        self.notifications = notifications
        self.audit = audit
        self.portal_base_url = portal_base_url.rstrip("/")

    async def stats(
        self,
        actor: AuthPrincipal,
        *,
        keyword: str | None = None,
        status: str | None = None,
        assignee_id: str | None = None,
    ) -> dict[str, int]:
        items = self.store.list_evaluations(
            tenant_id=actor.tenant_id, keyword=keyword, status=status, assignee_id=assignee_id
        )
        return {
            "total": len(items),
            "collecting": sum(1 for i in items if i.status == "collecting"),
            "aiReview": sum(1 for i in items if i.status == "ai_review"),
            "humanReview": sum(1 for i in items if i.status == "human_review"),
            "completed": sum(1 for i in items if i.status in {"completed", "closed"}),
            "risk": sum(1 for i in items if self.store.risk_count(i.id) > 0),
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
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        items = self.store.list_evaluations(
            tenant_id=actor.tenant_id, keyword=keyword, status=status, assignee_id=assignee_id
        )
        total = len(items)
        start = (page - 1) * page_size
        slice_items = items[start : start + page_size]
        data = [evaluation_dict(i, store=self.store) for i in slice_items]
        meta = {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size if page_size else 0,
        }
        return data, meta

    async def create_draft(self, actor: AuthPrincipal, payload: dict[str, Any]) -> dict[str, Any]:
        require_create(actor)
        now = _now()
        entity = EvaluationEntity(
            id=new_id(),
            tenant_id=actor.tenant_id,
            source_bid_task_id=_unwrap_id(payload.get("sourceBidTaskId")),
            project_name=str(payload["projectName"]).strip(),
            tender_no=str(payload["tenderNo"]).strip(),
            tender_entity=str(payload["tenderEntity"]).strip(),
            budget_amount=parse_money(_unwrap_root(payload["budgetAmount"])),
            currency=_unwrap_root(payload.get("currency", "CNY")),
            supplier_deadline=_parse_dt(_unwrap_root(payload["supplierDeadline"])),
            evaluation_start_at=_parse_dt(_unwrap_root(payload["evaluationStartAt"])),
            evaluation_end_at=_parse_dt(_unwrap_root(payload["evaluationEndAt"])),
            status="draft",
            current_step=1,
            progress_percent=5,
            assignee_id=_unwrap_id(payload["assigneeId"]),
            assignee_name=actor.name if _unwrap_id(payload["assigneeId"]) == actor.user_id else actor.name,
            description=(str(payload["description"]).strip() if payload.get("description") else None),
            version=1,
            created_at=now,
            updated_at=now,
        )
        self._assert_dates(entity)
        saved = self.store.save_evaluation(entity)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="evaluation",
                aggregate_id=saved.id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="evaluation.created",
                summary=f"创建评标草稿 {saved.project_name}",
            )
        )
        return evaluation_dict(saved, store=self.store)

    async def create_from_bid_task(
        self, actor: AuthPrincipal, bid_task_id: str, *, copy_materials: bool = True
    ) -> dict[str, Any]:
        require_create(actor)
        try:
            snapshot = await self.bid_snapshot.get_snapshot(
                tenant_id=actor.tenant_id,
                bid_task_id=bid_task_id,
            )
        except KeyError as exc:
            raise not_found("投标任务不存在或尚未接入") from exc
        now = _now()
        budget = snapshot.budget_amount if snapshot.budget_amount is not None else parse_money("0.00")
        entity = EvaluationEntity(
            id=new_id(),
            tenant_id=actor.tenant_id,
            source_bid_task_id=snapshot.id,
            project_name=snapshot.project_name,
            tender_no=snapshot.tender_no,
            tender_entity=snapshot.tender_entity,
            budget_amount=budget,
            currency="CNY",
            supplier_deadline=snapshot.deadline,
            evaluation_start_at=snapshot.deadline + timedelta(days=1),
            evaluation_end_at=snapshot.deadline + timedelta(days=7),
            status="draft",
            current_step=1,
            progress_percent=5,
            assignee_id=actor.user_id,
            assignee_name=actor.name,
            version=1,
            created_at=now,
            updated_at=now,
        )
        if copy_materials:
            entity.materials = [
                EvaluationMaterialEntity(
                    id=new_id(),
                    evaluation_id=entity.id,
                    name=m.name,
                    category=m.category,
                    required=m.required,
                    allowed_mime_types=list(m.allowed_mime_types),
                    max_size_bytes=m.max_size_bytes,
                    sort_order=m.sort_order,
                )
                for m in snapshot.materials
            ]
        saved = self.store.save_evaluation(entity)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="evaluation",
                aggregate_id=saved.id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="evaluation.imported_from_bid",
                summary=f"从投标任务 {bid_task_id} 导入评标草稿",
            )
        )
        return evaluation_detail_dict(saved, store=self.store)

    async def get_detail(self, actor: AuthPrincipal, evaluation_id: str) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_viewer(actor, entity)
        return evaluation_detail_dict(entity, store=self.store)

    async def list_audit_events(
        self,
        actor: AuthPrincipal,
        evaluation_id: str,
        *,
        page: int = 1,
        page_size: int = 20,
        actor_filter: str | None = None,
        action: str | None = None,
        resource: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_viewer(actor, entity)
        events, total = await self.audit.list_events(
            tenant_id=actor.tenant_id,
            aggregate_type="evaluation",
            aggregate_id=evaluation_id,
            actor=actor_filter,
            action=action,
            resource=resource,
            date_from=date_from,
            date_to=date_to,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return [_audit_event_dict(event) for event in events], {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size,
        }

    async def update(
        self, actor: AuthPrincipal, evaluation_id: str, payload: dict[str, Any], *, if_match: int | None
    ) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        if entity.status != "draft":
            raise conflict("仅草稿可修改基本信息", currentStatus=entity.status)
        self._assert_version(entity, if_match)
        if "projectName" in payload and payload["projectName"] is not None:
            entity.project_name = str(payload["projectName"]).strip()
        if "tenderNo" in payload and payload["tenderNo"] is not None:
            entity.tender_no = str(payload["tenderNo"]).strip()
        if "tenderEntity" in payload and payload["tenderEntity"] is not None:
            entity.tender_entity = str(payload["tenderEntity"]).strip()
        if "budgetAmount" in payload and payload["budgetAmount"] is not None:
            entity.budget_amount = parse_money(_unwrap_root(payload["budgetAmount"]))
        if "currency" in payload and payload["currency"] is not None:
            entity.currency = _unwrap_root(payload["currency"])
        if "supplierDeadline" in payload and payload["supplierDeadline"] is not None:
            entity.supplier_deadline = _parse_dt(_unwrap_root(payload["supplierDeadline"]))
        if "evaluationStartAt" in payload and payload["evaluationStartAt"] is not None:
            entity.evaluation_start_at = _parse_dt(_unwrap_root(payload["evaluationStartAt"]))
        if "evaluationEndAt" in payload and payload["evaluationEndAt"] is not None:
            entity.evaluation_end_at = _parse_dt(_unwrap_root(payload["evaluationEndAt"]))
        if "description" in payload:
            entity.description = str(payload["description"]).strip() if payload["description"] else None
        if "assigneeId" in payload and payload["assigneeId"] is not None:
            entity.assignee_id = _unwrap_id(payload["assigneeId"])
        self._assert_dates(entity)
        entity.version += 1
        entity.updated_at = _now()
        saved = self.store.save_evaluation(entity)
        return evaluation_dict(saved, store=self.store)

    async def put_materials(
        self, actor: AuthPrincipal, evaluation_id: str, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        if entity.status != "draft":
            raise conflict("仅草稿可配置材料")
        materials: list[EvaluationMaterialEntity] = []
        for raw in items:
            materials.append(
                EvaluationMaterialEntity(
                    id=_unwrap_id(raw.get("id")) or new_id(),
                    evaluation_id=evaluation_id,
                    name=str(raw["name"]).strip(),
                    category=_unwrap_root(raw["category"]),
                    required=bool(raw["required"]),
                    allowed_mime_types=list(raw["allowedMimeTypes"]),
                    max_size_bytes=int(raw["maxSizeBytes"]),
                    sort_order=int(raw["sortOrder"]),
                )
            )
        entity.materials = materials
        for supplier in entity.suppliers:
            supplier.required_material_count = sum(1 for m in materials if m.required)
        entity.version += 1
        entity.updated_at = _now()
        saved = self.store.save_evaluation(entity)
        return [material_dict(m) for m in saved.materials]

    async def put_criteria(
        self, actor: AuthPrincipal, evaluation_id: str, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        if entity.status != "draft":
            raise conflict("仅草稿可配置评分标准")
        criteria: list[ScoringCriterionEntity] = []
        for raw in items:
            criteria.append(
                ScoringCriterionEntity(
                    id=_unwrap_id(raw.get("id")) or new_id(),
                    evaluation_id=evaluation_id,
                    name=str(raw["name"]).strip(),
                    category=_unwrap_root(raw["category"]),
                    max_score=parse_score(_unwrap_root(raw["maxScore"])),
                    weight_percent=parse_weight(_unwrap_root(raw["weightPercent"])),
                    method=_unwrap_root(raw["method"]),
                    formula=(str(raw["formula"]) if raw.get("formula") else None),
                    description=str(raw.get("description", "")),
                    sort_order=int(raw["sortOrder"]),
                )
            )
        entity.criteria = criteria
        entity.version += 1
        entity.updated_at = _now()
        saved = self.store.save_evaluation(entity)
        return [criterion_dict(c) for c in saved.criteria]

    async def put_review_settings(
        self, actor: AuthPrincipal, evaluation_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        if entity.status != "draft":
            raise conflict("仅草稿可修改评审设置")
        entity.review_settings = ReviewSettingsEntity(
            multi_round_pricing=bool(payload["multiRoundPricing"]),
            max_rounds=int(payload["maxRounds"]),
            supplement_deadline_minutes=int(payload["supplementDeadlineMinutes"]),
            allow_modify_before_deadline=bool(payload["allowModifyBeforeDeadline"]),
            notify_on_missing=bool(payload["notifyOnMissing"]),
            close_submission_at_deadline=bool(payload["closeSubmissionAtDeadline"]),
        )
        entity.version += 1
        entity.updated_at = _now()
        saved = self.store.save_evaluation(entity)
        return review_settings_dict(saved)

    async def put_reviewers(
        self, actor: AuthPrincipal, evaluation_id: str, reviewer_ids: list[str]
    ) -> list[dict[str, str]]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        if entity.status != "draft":
            raise conflict("仅草稿可配置评委")
        ids = [_unwrap_id(i) for i in reviewer_ids]
        entity.reviewer_ids = ids
        for rid in ids:
            entity.reviewer_names.setdefault(rid, f"评审人-{rid[:8]}")
        entity.version += 1
        entity.updated_at = _now()
        saved = self.store.save_evaluation(entity)
        return [{"id": rid, "name": saved.reviewer_names.get(rid, rid)} for rid in saved.reviewer_ids]

    async def put_suppliers(
        self, actor: AuthPrincipal, evaluation_id: str, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        if entity.status != "draft":
            raise conflict("仅草稿可配置供应商")
        required = sum(1 for m in entity.materials if m.required)
        suppliers: list[SupplierEntity] = []
        for raw in items:
            suppliers.append(
                SupplierEntity(
                    id=new_id(),
                    evaluation_id=evaluation_id,
                    tenant_id=actor.tenant_id,
                    name=str(raw["name"]).strip(),
                    contact_name=str(raw["contactName"]).strip(),
                    email=str(raw["email"]).strip().lower(),
                    phone=(str(raw["phone"]).strip() if raw.get("phone") else None),
                    status="invited",
                    required_material_count=required,
                )
            )
        entity.suppliers = suppliers
        entity.version += 1
        entity.updated_at = _now()
        saved = self.store.save_evaluation(entity)
        return [supplier_dict(s) for s in saved.suppliers]

    async def validate(self, actor: AuthPrincipal, evaluation_id: str) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        return validate_evaluation(entity, now=_now())

    async def preview(self, actor: AuthPrincipal, evaluation_id: str) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        validation = validate_evaluation(entity, now=_now())
        return {
            "evaluation": evaluation_detail_dict(entity, store=self.store),
            "validation": validation,
            "supplierVisibleMaterials": [material_dict(m) for m in entity.materials],
        }

    async def publish(self, actor: AuthPrincipal, evaluation_id: str, *, idempotency_key: str | None) -> dict[str, Any]:
        if idempotency_key:
            cached = self.store.get_idempotency(f"publish:{idempotency_key}")
            if cached is not None:
                return cast(dict[str, Any], cached)
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        assert_evaluation_transition(entity.status, "collecting")
        validation = validate_evaluation(entity, now=_now())
        if not validation["valid"]:
            raise validation_error(
                "发布前校验未通过",
                field_errors=[
                    {"field": e["field"], "code": e["code"], "message": e["message"]} for e in validation["errors"]
                ],
            )
        now = _now()
        invites: list[dict[str, Any]] = []
        for supplier in entity.suppliers:
            raw, digest, masked = generate_invite_code()
            supplier.invite_code_hash = digest
            supplier.invite_code_masked = masked
            supplier.invite_status = "active"
            supplier.invite_expires_at = default_invite_expiry(now=now)
            supplier.invite_raw_once = raw
            self.store.invite_hash_index[digest] = supplier.id
            invites.append(
                {
                    "supplierId": supplier.id,
                    "supplierName": supplier.name,
                    "inviteCodeMasked": masked,
                    "inviteUrl": f"{self.portal_base_url}/{raw}",
                    "status": "active",
                    "expiresAt": supplier.invite_expires_at.isoformat().replace("+00:00", "Z"),
                }
            )
            await self.notifications.notify(
                NotificationInput(
                    tenant_id=actor.tenant_id,
                    user_id=None,
                    email=supplier.email,
                    type="task",
                    title="评标邀请",
                    content=f"您受邀参与项目 {entity.project_name} 的投标提交",
                    resource_type="evaluation",
                    resource_id=entity.id,
                )
            )
            supplier.invite_raw_once = None
        entity.status = "collecting"
        entity.current_step = evaluation_step_for("collecting")
        entity.progress_percent = evaluation_progress_for("collecting")
        entity.version += 1
        entity.updated_at = now
        saved = self.store.save_evaluation(entity)
        result = {"evaluation": evaluation_dict(saved, store=self.store), "invites": invites}
        if idempotency_key:
            self.store.remember_idempotency(f"publish:{idempotency_key}", result)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="evaluation",
                aggregate_id=saved.id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="evaluation.published",
                summary=f"发布评标并生成 {len(invites)} 个邀请",
            )
        )
        return result

    async def cancel(self, actor: AuthPrincipal, evaluation_id: str, reason: str) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        assert_evaluation_transition(entity.status, "cancelled")
        if entity.status == "collecting":
            has_submitted = any(s.status in {"submitted", "supplementing", "qualified"} for s in entity.suppliers)
            if has_submitted and actor.role != "admin":
                raise conflict("已有正式提交，仅管理员可强制取消")
        if not reason.strip():
            raise validation_error("取消原因必填")
        entity.status = "cancelled"
        entity.current_step = evaluation_step_for("cancelled")
        entity.progress_percent = evaluation_progress_for("cancelled")
        entity.version += 1
        entity.updated_at = _now()
        saved = self.store.save_evaluation(entity)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="evaluation",
                aggregate_id=saved.id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="evaluation.cancelled",
                summary=f"取消评标：{reason.strip()}",
            )
        )
        return evaluation_dict(saved, store=self.store)

    async def close(
        self, actor: AuthPrincipal, evaluation_id: str, result_summary: str, *, idempotency_key: str | None
    ) -> dict[str, Any]:
        if idempotency_key:
            cached = self.store.get_idempotency(f"close:{idempotency_key}")
            if cached is not None:
                return cast(dict[str, Any], cached)
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        assert_evaluation_transition(entity.status, "closed")
        if entity.supplier_deadline > _now() and entity.status == "collecting":
            raise deadline_passed("收集期未结束，不能关闭")
        entity.status = "closed"
        entity.result_summary = result_summary.strip()
        entity.current_step = 6
        entity.progress_percent = 100
        entity.version += 1
        entity.updated_at = _now()
        for supplier in entity.suppliers:
            if supplier.invite_status == "active":
                supplier.invite_status = "expired"
        saved = self.store.save_evaluation(entity)
        result = evaluation_dict(saved, store=self.store)
        if idempotency_key:
            self.store.remember_idempotency(f"close:{idempotency_key}", result)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="evaluation",
                aggregate_id=saved.id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="evaluation.closed",
                summary=f"关闭评标：{result_summary.strip()}",
            )
        )
        return result

    async def list_suppliers(
        self, actor: AuthPrincipal, evaluation_id: str, *, page: int = 1, page_size: int = 20, status: str | None = None
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_viewer(actor, entity)
        items = entity.suppliers
        if status:
            items = [s for s in items if s.status == status]
        total = len(items)
        start = (page - 1) * page_size
        data = [supplier_dict(s) for s in items[start : start + page_size]]
        meta = {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size if page_size else 0,
        }
        return data, meta

    async def list_invites(self, actor: AuthPrincipal, evaluation_id: str) -> list[dict[str, Any]]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        result = []
        for s in entity.suppliers:
            result.append(
                {
                    "supplierId": s.id,
                    "supplierName": s.name,
                    "inviteCodeMasked": s.invite_code_masked or "****",
                    "inviteUrl": f"{self.portal_base_url}/masked",
                    "status": s.invite_status,
                    "expiresAt": (
                        s.invite_expires_at.isoformat().replace("+00:00", "Z")
                        if s.invite_expires_at
                        else _now().isoformat().replace("+00:00", "Z")
                    ),
                }
            )
        return result

    async def rotate_invite(
        self, actor: AuthPrincipal, evaluation_id: str, supplier_id: str, reason: str
    ) -> dict[str, Any]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        supplier = self._supplier(entity, supplier_id)
        if supplier.invite_code_hash:
            self.store.invite_hash_index.pop(supplier.invite_code_hash, None)
        raw, digest, masked = generate_invite_code()
        supplier.invite_code_hash = digest
        supplier.invite_code_masked = masked
        supplier.invite_status = "active"
        supplier.invite_expires_at = default_invite_expiry()
        self.store.invite_hash_index[digest] = supplier.id
        entity.updated_at = _now()
        entity.version += 1
        self.store.save_evaluation(entity)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="evaluation",
                aggregate_id=entity.id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="supplier.invite_rotated",
                summary=f"轮换邀请码：{reason}",
                target_type="supplier",
                target_id=supplier_id,
            )
        )
        return {
            "supplierId": supplier.id,
            "supplierName": supplier.name,
            "inviteCodeMasked": masked,
            "inviteUrl": f"{self.portal_base_url}/{raw}",
            "status": "active",
            "expiresAt": supplier.invite_expires_at.isoformat().replace("+00:00", "Z"),
        }

    async def revoke_invite(
        self, actor: AuthPrincipal, evaluation_id: str, supplier_id: str, reason: str
    ) -> dict[str, bool]:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_owner(actor, entity)
        supplier = self._supplier(entity, supplier_id)
        if supplier.invite_code_hash:
            self.store.invite_hash_index.pop(supplier.invite_code_hash, None)
        supplier.invite_status = "revoked"
        supplier.invite_code_hash = None
        entity.updated_at = _now()
        self.store.save_evaluation(entity)
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="evaluation",
                aggregate_id=entity.id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action="supplier.invite_revoked",
                summary=f"撤销邀请：{reason}",
                target_type="supplier",
                target_id=supplier_id,
            )
        )
        return {"revoked": True}

    async def enqueue_job(
        self, actor: AuthPrincipal, evaluation_id: str, job_type: str, *, idempotency_key: str | None = None
    ) -> JobRefSnapshot:
        entity = self.store.get_evaluation(evaluation_id, tenant_id=actor.tenant_id)
        require_viewer(actor, entity)
        job = await self.jobs.enqueue(
            tenant_id=actor.tenant_id,
            job_type=job_type,
            payload={"evaluationId": evaluation_id},
            created_by=actor.user_id,
            idempotency_key=idempotency_key,
        )
        entity.latest_job_ids = [job.id, *entity.latest_job_ids][:10]
        entity.updated_at = _now()
        self.store.save_evaluation(entity)
        return job

    def _supplier(self, entity: EvaluationEntity, supplier_id: str) -> SupplierEntity:
        for supplier in entity.suppliers:
            if supplier.id == supplier_id:
                return supplier
        raise not_found("供应商不存在", supplierId=supplier_id)

    def _assert_version(self, entity: EvaluationEntity, if_match: int | None) -> None:
        if if_match is None:
            raise validation_error("PATCH 必须提供 If-Match 版本")
        if if_match != entity.version:
            raise version_conflict(entity.version)

    def _assert_dates(self, entity: EvaluationEntity) -> None:
        if entity.supplier_deadline >= entity.evaluation_start_at:
            raise validation_error("供应商截止时间必须早于评标开始时间")
        if entity.evaluation_start_at >= entity.evaluation_end_at:
            raise validation_error("评标结束时间必须晚于开始时间")


def _unwrap_root(value: Any) -> Any:
    return getattr(value, "root", value)


def _unwrap_id(value: Any) -> str:
    if value is None:
        return ""
    raw = getattr(value, "root", value)
    return str(raw)
