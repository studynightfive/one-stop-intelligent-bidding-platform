"""供应商门户服务：会话、材料、提交、补材料、活动。"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from app.domains.evaluations.entities import (
    PortalActivityEntity,
    PortalDraftEntity,
    PortalSessionEntity,
    SupplierSubmissionEntity,
)
from app.domains.evaluations.errors import (
    conflict,
    deadline_passed,
    forbidden,
    not_found,
    validation_error,
)
from app.domains.evaluations.ids import new_id
from app.domains.evaluations.mappers import evaluation_dict, file_ref_dict, notice_dict, supplier_dict
from app.domains.evaluations.money import format_money, parse_money
from app.domains.evaluations.ports import (
    AuditEventInput,
    AuditServicePort,
    FileServicePort,
    PortalPrincipal,
)
from app.domains.evaluations.state_machine import assert_supplier_transition
from app.domains.evaluations.store import EvaluationStore
from app.domains.portal.security import (
    default_portal_token_expiry,
    generate_portal_access_token,
    hash_secret,
)
from app.domains.evaluations.pdf_util import build_simple_pdf


PORTAL_REFRESH_COOKIE = "portal_refresh_token"


def _now() -> datetime:
    return datetime.now(UTC)


class PortalService:
    def __init__(
        self,
        store: EvaluationStore,
        *,
        files: FileServicePort,
        audit: AuditServicePort,
    ) -> None:
        self.store = store
        self.files = files
        self.audit = audit

    async def exchange(self, invite_code: str) -> dict[str, Any]:
        digest = hash_secret(invite_code)
        supplier_id = self.store.invite_hash_index.get(digest)
        if not supplier_id:
            raise forbidden("邀请码无效或已失效")
        # 定位评标
        entity = None
        supplier = None
        for evaluation in self.store.evaluations.values():
            for item in evaluation.suppliers:
                if item.id == supplier_id:
                    entity = evaluation
                    supplier = item
                    break
            if entity:
                break
        if entity is None or supplier is None:
            raise forbidden("邀请码无效或已失效")
        if entity.tenant_id != supplier.tenant_id:
            raise forbidden("邀请码无效或已失效")
        if entity.status in {"closed", "cancelled"}:
            raise conflict("评标已结束，门户不可用", currentStatus=entity.status)
        if supplier.invite_status in {"revoked", "expired"}:
            raise forbidden("邀请码已撤销或过期")
        if supplier.invite_expires_at and supplier.invite_expires_at < _now():
            supplier.invite_status = "expired"
            self.store.save_evaluation(entity)
            raise forbidden("邀请码已过期")
        # 单次交换：active -> used
        if supplier.invite_status == "used":
            raise forbidden("邀请码已被使用，请勿重放")
        if supplier.invite_status == "active":
            supplier.invite_status = "used"
        raw_token, token_hash = generate_portal_access_token()
        refresh_raw, refresh_hash = generate_portal_access_token()
        expires = default_portal_token_expiry()
        refresh_expires = default_portal_token_expiry(minutes=60 * 24 * 7)
        session = PortalSessionEntity(
            token_id=new_id(),
            access_token=raw_token,
            supplier_id=supplier.id,
            evaluation_id=entity.id,
            tenant_id=entity.tenant_id,
            expires_at=expires,
            refresh_token=refresh_raw,
            refresh_expires_at=refresh_expires,
        )
        self.store.save_session(session)
        self.store.token_hash_index[token_hash] = session.token_id
        self.store.refresh_hash_index[refresh_hash] = session.token_id
        self.store.invite_hash_index.pop(digest, None)
        supplier.invite_code_hash = None
        entity.updated_at = _now()
        self.store.save_evaluation(entity)
        await self.audit.append(
            AuditEventInput(
                tenant_id=entity.tenant_id,
                aggregate_type="supplier",
                aggregate_id=supplier.id,
                actor_type="supplier",
                actor_id=supplier.id,
                actor_name=supplier.name,
                action="portal.session_exchanged",
                summary="邀请码交换门户会话",
            )
        )
        return {
            "portalAccessToken": raw_token,
            "accessTokenExpiresAt": expires.isoformat().replace("+00:00", "Z"),
            "supplier": supplier_dict(supplier),
            "refreshToken": refresh_raw,
            "refreshTokenExpiresAt": refresh_expires.isoformat().replace("+00:00", "Z"),
        }

    def resolve_principal(self, access_token: str) -> PortalPrincipal:
        token_hash = hash_secret(access_token)
        token_id = self.store.token_hash_index.get(token_hash)
        if not token_id:
            raise forbidden("门户令牌无效")
        session = self.store.get_session(token_id)
        if session.expires_at < _now():
            raise forbidden("门户令牌已过期")
        entity = self.store.get_evaluation(session.evaluation_id, tenant_id=session.tenant_id)
        supplier = next((s for s in entity.suppliers if s.id == session.supplier_id), None)
        if supplier is None:
            raise forbidden("门户令牌无效")
        return PortalPrincipal(
            supplier_id=supplier.id,
            evaluation_id=entity.id,
            tenant_id=entity.tenant_id,
            name=supplier.name,
        )

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        """使用 Portal Refresh Cookie 中的 refresh_token 轮换会话。"""
        refresh_hash = hash_secret(refresh_token)
        token_id = self.store.refresh_hash_index.get(refresh_hash)
        if not token_id:
            raise forbidden("门户刷新令牌无效")
        old = self.store.get_session(token_id)
        if old.refresh_expires_at and old.refresh_expires_at < _now():
            raise forbidden("门户刷新令牌已过期")
        # 吊销旧会话
        self.store.refresh_hash_index.pop(refresh_hash, None)
        old_access_hash = hash_secret(old.access_token)
        self.store.token_hash_index.pop(old_access_hash, None)
        old.revoked = True
        self.store.save_session(old)

        raw_token, token_hash = generate_portal_access_token()
        refresh_raw, new_refresh_hash = generate_portal_access_token()
        expires = default_portal_token_expiry()
        refresh_expires = default_portal_token_expiry(minutes=60 * 24 * 7)
        session = PortalSessionEntity(
            token_id=new_id(),
            access_token=raw_token,
            supplier_id=old.supplier_id,
            evaluation_id=old.evaluation_id,
            tenant_id=old.tenant_id,
            expires_at=expires,
            refresh_token=refresh_raw,
            refresh_expires_at=refresh_expires,
        )
        self.store.save_session(session)
        self.store.token_hash_index[token_hash] = session.token_id
        self.store.refresh_hash_index[new_refresh_hash] = session.token_id
        entity = self.store.get_evaluation(old.evaluation_id, tenant_id=old.tenant_id)
        supplier = next(s for s in entity.suppliers if s.id == old.supplier_id)
        return {
            "portalAccessToken": raw_token,
            "accessTokenExpiresAt": expires.isoformat().replace("+00:00", "Z"),
            "supplier": supplier_dict(supplier),
            "refreshToken": refresh_raw,
            "refreshTokenExpiresAt": refresh_expires.isoformat().replace("+00:00", "Z"),
        }

    async def logout(self, access_token: str, refresh_token: str | None = None) -> dict[str, bool]:
        if access_token:
            token_hash = hash_secret(access_token)
            token_id = self.store.token_hash_index.pop(token_hash, None)
            if token_id and token_id in self.store.sessions:
                session = self.store.sessions[token_id]
                session.revoked = True
                if session.refresh_token:
                    self.store.refresh_hash_index.pop(hash_secret(session.refresh_token), None)
        if refresh_token:
            rh = hash_secret(refresh_token)
            tid = self.store.refresh_hash_index.pop(rh, None)
            if tid and tid in self.store.sessions:
                self.store.sessions[tid].revoked = True
        return {"loggedOut": True}

    async def build_receipt_pdf(self, portal: PortalPrincipal) -> tuple[bytes, str, str]:
        """返回 (pdf_bytes, file_name, sha256)。"""
        entity = self.store.get_evaluation(portal.evaluation_id, tenant_id=portal.tenant_id)
        supplier = next(s for s in entity.suppliers if s.id == portal.supplier_id)
        submissions = [
            s
            for s in self.store.list_submissions(evaluation_id=entity.id, supplier_id=portal.supplier_id)
            if s.status in {"submitted", "replaced"}
        ]
        if not submissions and supplier.status not in {"submitted", "qualified", "disqualified"}:
            raise not_found("尚无正式提交回执")
        receipt_no = f"R-{(supplier.submitted_at or _now()).strftime('%Y%m%d')}-{supplier.id[:8].upper()}"
        lines = [
            "Submission Receipt",
            f"Receipt: {receipt_no}",
            f"Project: {entity.project_name}",
            f"Supplier: {supplier.name}",
            f"Materials: {len(submissions)}",
            f"Status: {supplier.status}",
        ]
        pdf = build_simple_pdf(lines)
        digest = hashlib.sha256(pdf).hexdigest()
        return pdf, f"{receipt_no}.pdf", digest

    async def me(self, portal: PortalPrincipal) -> dict[str, Any]:
        entity = self.store.get_evaluation(portal.evaluation_id, tenant_id=portal.tenant_id)
        supplier = next(s for s in entity.suppliers if s.id == portal.supplier_id)
        required = sum(1 for m in entity.materials if m.required)
        submitted = len(
            [
                s
                for s in self.store.list_submissions(evaluation_id=entity.id, supplier_id=supplier.id)
                if s.status in {"submitted", "replaced"}
            ]
        )
        missing = max(required - submitted, 0)
        allowed = []
        if entity.status == "collecting" and _now() <= entity.supplier_deadline:
            allowed.extend(["upload", "draft", "submit"])
        if entity.status == "closed":
            allowed = ["view"]
        return {
            "evaluation": evaluation_dict(entity, store=self.store),
            "supplier": supplier_dict(supplier),
            "submissionSummary": {
                "required": required,
                "submitted": submitted,
                "missing": missing,
                "finalSubmitted": supplier.status in {"submitted", "qualified", "disqualified"},
            },
            "allowedActions": allowed,
        }

    async def list_materials(self, portal: PortalPrincipal) -> list[dict[str, Any]]:
        entity = self.store.get_evaluation(portal.evaluation_id, tenant_id=portal.tenant_id)
        result = []
        for material in sorted(entity.materials, key=lambda m: m.sort_order):
            submission = self.store.find_submission(supplier_id=portal.supplier_id, material_id=material.id)
            status = "missing"
            file_data = None
            submitted_at = None
            if submission:
                status = "draft" if submission.status == "draft" else "submitted"
                file_obj = await self.files.get_file(tenant_id=portal.tenant_id, file_id=submission.file_id)
                file_data = file_ref_dict(file_obj)
                submitted_at = submission.submitted_at
            item: dict[str, Any] = {
                "id": material.id,
                "name": material.name,
                "category": material.category,
                "required": material.required,
                "allowedMimeTypes": list(material.allowed_mime_types),
                "maxSizeBytes": material.max_size_bytes,
                "status": status,
            }
            if file_data:
                item["file"] = file_data
            if submitted_at:
                item["submittedAt"] = submitted_at.isoformat().replace("+00:00", "Z")
            result.append(item)
        return result

    def _assert_open(self, portal: PortalPrincipal) -> Any:
        entity = self.store.get_evaluation(portal.evaluation_id, tenant_id=portal.tenant_id)
        if entity.status in {"closed", "cancelled"}:
            raise conflict("评标已关闭")
        if entity.status != "collecting":
            # 补材料期允许 supplementing
            supplier = next(s for s in entity.suppliers if s.id == portal.supplier_id)
            if supplier.status != "supplementing":
                raise conflict("当前不可修改材料", currentStatus=entity.status)
        if _now() > entity.supplier_deadline and entity.review_settings.close_submission_at_deadline:
            supplier = next(s for s in entity.suppliers if s.id == portal.supplier_id)
            if supplier.status != "supplementing":
                raise deadline_passed("已过供应商截止时间")
        return entity

    async def put_material_file(self, portal: PortalPrincipal, material_id: str, file_id: str) -> dict[str, Any]:
        entity = self._assert_open(portal)
        material = next((m for m in entity.materials if m.id == material_id), None)
        if material is None:
            raise not_found("材料项不存在")
        file_obj = await self.files.assert_accessible(
            tenant_id=portal.tenant_id,
            file_id=file_id,
            actor_id=portal.supplier_id,
            purpose="supplierMaterial",
        )
        if file_obj.scan_status == "infected":
            raise validation_error("文件病毒扫描未通过")
        now = _now()
        existing = self.store.find_submission(supplier_id=portal.supplier_id, material_id=material_id)
        if existing:
            existing.file_id = file_id
            existing.status = "draft"
            existing.version += 1
            existing.replaced_at = now
            saved = self.store.save_submission(existing)
        else:
            saved = self.store.save_submission(
                SupplierSubmissionEntity(
                    id=new_id(),
                    evaluation_id=entity.id,
                    supplier_id=portal.supplier_id,
                    material_id=material_id,
                    file_id=file_id,
                    status="draft",
                )
            )
        supplier = next(s for s in entity.suppliers if s.id == portal.supplier_id)
        if supplier.status == "invited":
            assert_supplier_transition("invited", "partial")
            supplier.status = "partial"
        draft_count = len(
            [
                s
                for s in self.store.list_submissions(evaluation_id=entity.id, supplier_id=portal.supplier_id)
                if s.status in {"draft", "submitted", "replaced"}
            ]
        )
        supplier.submitted_material_count = draft_count
        entity.updated_at = now
        self.store.save_evaluation(entity)
        materials = await self.list_materials(portal)
        return next(m for m in materials if m["id"] == material_id)

    async def delete_material_file(self, portal: PortalPrincipal, material_id: str) -> dict[str, Any]:
        entity = self._assert_open(portal)
        existing = self.store.find_submission(supplier_id=portal.supplier_id, material_id=material_id)
        if existing and existing.id in self.store.submissions:
            del self.store.submissions[existing.id]
        supplier = next(s for s in entity.suppliers if s.id == portal.supplier_id)
        supplier.submitted_material_count = len(
            self.store.list_submissions(evaluation_id=entity.id, supplier_id=portal.supplier_id)
        )
        self.store.save_evaluation(entity)
        materials = await self.list_materials(portal)
        return next(m for m in materials if m["id"] == material_id)

    async def save_draft(self, portal: PortalPrincipal, payload: dict[str, Any]) -> dict[str, Any]:
        self._assert_open(portal)
        now = _now()
        existing = self.store.get_draft(portal.supplier_id)
        version = (existing.version + 1) if existing else 1
        quote = None
        if payload.get("quoteDraft") is not None:
            quote = parse_money(str(getattr(payload["quoteDraft"], "root", payload["quoteDraft"])))
        draft = PortalDraftEntity(
            supplier_id=portal.supplier_id,
            evaluation_id=portal.evaluation_id,
            note=(str(payload["note"]).strip() if payload.get("note") else None),
            quote_draft=quote,
            saved_at=now,
            version=version,
        )
        saved = self.store.save_draft(draft)
        data: dict[str, Any] = {
            "supplierId": saved.supplier_id,
            "savedAt": now.isoformat().replace("+00:00", "Z"),
            "version": saved.version,
        }
        if saved.note:
            data["note"] = saved.note
        if saved.quote_draft is not None:
            data["quoteDraft"] = format_money(saved.quote_draft)
        return data

    async def submit(self, portal: PortalPrincipal, *, confirmed: bool, idempotency_key: str | None) -> dict[str, Any]:
        if not confirmed:
            raise validation_error("必须确认正式提交")
        if idempotency_key:
            cached = self.store.get_idempotency(f"portal-submit:{idempotency_key}")
            if cached is not None:
                return cached
        entity = self._assert_open(portal)
        supplier = next(s for s in entity.suppliers if s.id == portal.supplier_id)
        required_ids = [m.id for m in entity.materials if m.required]
        submissions = self.store.list_submissions(evaluation_id=entity.id, supplier_id=portal.supplier_id)
        by_material = {s.material_id: s for s in submissions}
        missing = [mid for mid in required_ids if mid not in by_material]
        if missing:
            raise validation_error("仍有必交材料未上传", field_errors=[
                {"field": "materials", "code": "MISSING", "message": f"缺少材料 {mid}"} for mid in missing
            ])
        now = _now()
        sha_parts: list[str] = []
        for submission in submissions:
            submission.status = "submitted"
            submission.submitted_at = now
            submission.version += 1
            self.store.save_submission(submission)
            file_obj = await self.files.get_file(tenant_id=portal.tenant_id, file_id=submission.file_id)
            sha_parts.append(file_obj.sha256)
        if supplier.status in {"invited", "partial", "supplementing"}:
            target = "submitted"
            assert_supplier_transition(supplier.status, target)
            supplier.status = target
        supplier.submitted_at = now
        supplier.submitted_material_count = len(submissions)
        entity.updated_at = now
        self.store.save_evaluation(entity)
        receipt_no = f"R-{now.strftime('%Y%m%d')}-{supplier.id[:8].upper()}"
        digest = hashlib.sha256("|".join(sorted(sha_parts)).encode("utf-8")).hexdigest()
        receipt = {
            "receiptNo": receipt_no,
            "evaluationId": entity.id,
            "supplierId": supplier.id,
            "submittedAt": now.isoformat().replace("+00:00", "Z"),
            "submittedMaterialCount": len(submissions),
            "sha256": digest,
        }
        if idempotency_key:
            self.store.remember_idempotency(f"portal-submit:{idempotency_key}", receipt)
        self.store.add_activity(
            PortalActivityEntity(
                id=new_id(),
                evaluation_id=entity.id,
                supplier_id=supplier.id,
                action="submit",
                summary="正式提交材料",
                occurred_at=now,
            )
        )
        await self.audit.append(
            AuditEventInput(
                tenant_id=portal.tenant_id,
                aggregate_type="supplier",
                aggregate_id=supplier.id,
                actor_type="supplier",
                actor_id=supplier.id,
                actor_name=supplier.name,
                action="portal.submitted",
                summary=f"正式提交回执 {receipt_no}",
            )
        )
        return receipt

    async def list_notices(self, portal: PortalPrincipal) -> list[dict[str, Any]]:
        items = self.store.list_notices(evaluation_id=portal.evaluation_id, supplier_id=portal.supplier_id)
        return [notice_dict(n) for n in items]

    async def respond_notice(
        self, portal: PortalPrincipal, notice_id: str, file_bindings: list[dict[str, str]]
    ) -> dict[str, Any]:
        notice = self.store.get_notice(notice_id)
        if notice.supplier_id != portal.supplier_id or notice.evaluation_id != portal.evaluation_id:
            raise forbidden("无权处理该通知")
        if notice.deadline < _now():
            raise deadline_passed("补材料期限已过")
        for binding in file_bindings:
            await self.put_material_file(portal, binding["materialId"], binding["fileId"])
        notice.status = "responded"
        notice.responded_at = _now()
        saved = self.store.save_notice(notice)
        entity = self.store.get_evaluation(portal.evaluation_id, tenant_id=portal.tenant_id)
        supplier = next(s for s in entity.suppliers if s.id == portal.supplier_id)
        if supplier.status == "supplementing":
            assert_supplier_transition("supplementing", "submitted")
            supplier.status = "submitted"
            self.store.save_evaluation(entity)
        return notice_dict(saved)

    async def list_price_rounds(self, portal: PortalPrincipal) -> list[dict[str, Any]]:
        from app.domains.evaluations.mappers import quote_dict, round_dict

        rounds = self.store.list_rounds(evaluation_id=portal.evaluation_id)
        result = []
        for item in rounds:
            if portal.supplier_id not in item.eligible_supplier_ids:
                continue
            count = len(self.store.list_quotes(evaluation_id=portal.evaluation_id, round_id=item.id))
            data = round_dict(item, submission_count=count)
            my_quote = self.store.find_quote(round_id=item.id, supplier_id=portal.supplier_id)
            if my_quote:
                data["myQuote"] = quote_dict(my_quote)
            quotes = sorted(
                self.store.list_quotes(evaluation_id=portal.evaluation_id, round_id=item.id),
                key=lambda q: q.amount,
            )
            if item.ranking_visible_to_supplier and my_quote:
                for idx, q in enumerate(quotes, start=1):
                    if q.supplier_id == portal.supplier_id:
                        data["myRank"] = idx
                        break
            data["rankingVisible"] = item.ranking_visible_to_supplier
            result.append(data)
        return result

    async def list_activity(
        self, portal: PortalPrincipal, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        items = self.store.list_activities(evaluation_id=portal.evaluation_id, supplier_id=portal.supplier_id)
        total = len(items)
        start = (page - 1) * page_size
        data = [
            {
                "id": a.id,
                "action": a.action,
                "summary": a.summary,
                "occurredAt": a.occurred_at.isoformat().replace("+00:00", "Z"),
            }
            for a in items[start : start + page_size]
        ]
        meta = {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size if page_size else 0,
        }
        return data, meta
