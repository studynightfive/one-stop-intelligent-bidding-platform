"""资质库业务服务。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Any, cast

from app.domains.bids.access import require_internal
from app.domains.bids.binary import build_xlsx
from app.domains.bids.errors import (
    conflict,
    file_rejected,
    forbidden,
    not_found,
    validation_error,
    version_conflict,
)
from app.domains.bids.ids import new_id
from app.domains.bids.ports import (
    AuditEventInput,
    AuditServicePort,
    AuthPrincipal,
    FileRefSnapshot,
    FileServicePort,
    JobDispatcherPort,
    JobRefSnapshot,
    NotificationInput,
    NotificationServicePort,
)
from app.domains.qualifications.entities import (
    QualificationEntity,
    QualificationImportBindingEntity,
    QualificationVersionEntity,
    qualification_status,
)
from app.domains.qualifications.store import QualificationStore

_CREATE_FIELDS = {
    "name",
    "category",
    "certNumber",
    "issuer",
    "validFrom",
    "expiryDate",
    "fileId",
    "documentVersion",
    "reminderDays",
    "tags",
}
_UPDATE_FIELDS = _CREATE_FIELDS - {"fileId"}
_IMPORT_CATEGORY = "qualification.import"
_IMPORT_ROW_FIELDS = _CREATE_FIELDS - {"fileId"}
_SORT_FIELDS = {
    "name": lambda item: item.name.casefold(),
    "category": lambda item: item.category.casefold(),
    "expiryDate": lambda item: item.expiry_date or date.max,
    "createdAt": lambda item: item.created_at or datetime.min.replace(tzinfo=UTC),
    "updatedAt": lambda item: item.updated_at or datetime.min.replace(tzinfo=UTC),
}


def _now() -> datetime:
    return datetime.now(UTC)


def _require_writer(actor: AuthPrincipal) -> None:
    if actor.role not in {"admin", "project_lead"}:
        raise forbidden("仅管理员或项目负责人可维护资质")


def _require_admin(actor: AuthPrincipal) -> None:
    if actor.role != "admin":
        raise forbidden("仅管理员可删除资质")


def _require_clean(file: FileRefSnapshot) -> None:
    if file.scan_status != "clean":
        raise file_rejected("文件安全扫描尚未通过", fileId=file.id, scanStatus=file.scan_status)
    digest = str(file.sha256 or "")
    if len(digest) != 64 or digest == "0" * 64 or any(char not in "0123456789abcdefABCDEF" for char in digest):
        raise file_rejected("文件 SHA-256 摘要无效", fileId=file.id)


def _text(value: Any, field: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise validation_error(
            f"{field} 不能为空",
            field_errors=[{"field": field, "code": "REQUIRED", "message": "不能为空"}],
        )
    return cleaned


def _optional_date(value: Any, field: str) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise validation_error(
            f"{field} 必须为 YYYY-MM-DD",
            field_errors=[{"field": field, "code": "FORMAT", "message": "日期格式错误"}],
        ) from exc


def _validate_dates(valid_from: date | None, expiry_date: date | None) -> None:
    if valid_from is not None and expiry_date is not None and valid_from > expiry_date:
        raise validation_error(
            "有效期起始日不得晚于到期日",
            field_errors=[{"field": "expiryDate", "code": "DATE_RANGE", "message": "不得早于 validFrom"}],
        )


def _int_list(value: Any, field: str) -> list[int]:
    if not isinstance(value, list):
        raise validation_error(f"{field} 必须为数组")
    result: list[int] = []
    for item in value:
        raw = getattr(item, "root", item)
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            raise validation_error(f"{field} 只能包含非负整数")
        if raw not in result:
            result.append(raw)
    return result


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise validation_error(f"{field} 必须为数组")
    result: list[str] = []
    for item in value:
        cleaned = str(item).strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _reject_unknown(payload: Mapping[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise validation_error(
            "请求包含未知字段",
            field_errors=[{"field": field, "code": "UNKNOWN_FIELD", "message": "不允许的字段"} for field in unknown],
        )


def _import_text(row: Mapping[str, Any], field: str, row_number: int) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        path = f"rows[{row_number}].{field}"
        raise validation_error(
            f"导入第 {row_number} 行 {field} 必须为非空字符串",
            field_errors=[{"field": path, "code": "TYPE", "message": "必须为非空字符串"}],
        )
    return value.strip()


def _import_tags(row: Mapping[str, Any], row_number: int) -> list[str]:
    value = row.get("tags")
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise validation_error(
            f"导入第 {row_number} 行 tags 必须为字符串数组",
            field_errors=[{"field": f"rows[{row_number}].tags", "code": "TYPE", "message": "必须为字符串数组"}],
        )
    return list(dict.fromkeys(item.strip() for item in value if item.strip()))


def _file_dict(file: FileRefSnapshot) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": file.id,
        "fileName": file.file_name,
        "mimeType": file.mime_type,
        "sizeBytes": file.size_bytes,
        "sha256": file.sha256,
        "scanStatus": file.scan_status,
        "createdAt": file.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }
    if file.preview_url is not None:
        data["previewUrl"] = file.preview_url
    if file.download_url is not None:
        data["downloadUrl"] = file.download_url
    return data


def qualification_dict(entity: QualificationEntity) -> dict[str, Any]:
    assert entity.created_at is not None and entity.updated_at is not None
    data: dict[str, Any] = {
        "id": entity.id,
        "name": entity.name,
        "category": entity.category,
        "certNumber": entity.cert_number,
        "issuer": entity.issuer,
        "status": qualification_status(entity),
        "file": _file_dict(entity.file),
        "documentVersion": entity.document_version,
        "reminderDays": entity.reminder_days,
        "tags": entity.tags,
        "version": entity.version,
        "createdAt": entity.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "updatedAt": entity.updated_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }
    if entity.valid_from is not None:
        data["validFrom"] = entity.valid_from.isoformat()
    if entity.expiry_date is not None:
        data["expiryDate"] = entity.expiry_date.isoformat()
    return data


def job_dict(job: JobRefSnapshot) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "progressPercent": job.progress_percent,
        "createdAt": job.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }
    if job.current_step is not None:
        data["currentStep"] = job.current_step
    return data


class QualificationService:
    def __init__(
        self,
        store: QualificationStore,
        *,
        files: FileServicePort,
        jobs: JobDispatcherPort,
        audit: AuditServicePort,
        notifications: NotificationServicePort,
    ) -> None:
        self.store = store
        self.files = files
        self.jobs = jobs
        self.audit = audit
        self.notifications = notifications

    async def stats(self, actor: AuthPrincipal) -> dict[str, int]:
        require_internal(actor)
        statuses = [qualification_status(item) for item in self.store.list(tenant_id=actor.tenant_id)]
        return {
            "total": len(statuses),
            "valid": statuses.count("valid"),
            "expiring": statuses.count("expiring"),
            "expired": statuses.count("expired"),
        }

    async def list_qualifications(
        self,
        actor: AuthPrincipal,
        *,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "desc",
        keyword: str | None = None,
        category: str | None = None,
        status: str | None = None,
        expires_within_days: int | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        require_internal(actor)
        items = self.store.list(tenant_id=actor.tenant_id)
        if keyword:
            needle = keyword.strip().casefold()
            items = [
                item
                for item in items
                if any(
                    needle in value.casefold()
                    for value in (item.name, item.category, item.cert_number, item.issuer, *item.tags)
                )
            ]
        if category:
            items = [item for item in items if item.category == category]
        if status:
            if status not in {"valid", "expiring", "expired", "revoked"}:
                raise validation_error("status 不合法")
            items = [item for item in items if qualification_status(item) == status]
        if expires_within_days is not None:
            if expires_within_days < 0:
                raise validation_error("expiresWithinDays 不得小于 0")
            today = date.today()
            items = [
                item
                for item in items
                if item.expiry_date is not None and 0 <= (item.expiry_date - today).days <= expires_within_days
            ]
        if sort_order not in {"asc", "desc"}:
            raise validation_error("sortOrder 仅支持 asc 或 desc")
        if sort_by is not None and sort_by not in _SORT_FIELDS:
            raise validation_error("sortBy 不受支持")
        sort_key = _SORT_FIELDS.get(sort_by or "updatedAt")
        assert sort_key is not None
        items.sort(key=sort_key, reverse=sort_order == "desc")
        total = len(items)
        start = (page - 1) * page_size
        page_items = items[start : start + page_size]
        total_pages = (total + page_size - 1) // page_size if total else 0
        return [qualification_dict(item) for item in page_items], {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": total_pages,
        }

    async def create(self, actor: AuthPrincipal, payload: Mapping[str, Any]) -> dict[str, Any]:
        _require_writer(actor)
        _reject_unknown(payload, _CREATE_FIELDS)
        valid_from = _optional_date(payload.get("validFrom"), "validFrom")
        expiry_date = _optional_date(payload.get("expiryDate"), "expiryDate")
        _validate_dates(valid_from, expiry_date)
        file_id = _text(payload.get("fileId"), "fileId")
        file = await self._accessible_file(actor, file_id)
        now = _now()
        cert_number = _text(payload.get("certNumber"), "certNumber")
        if self.store.cert_number_exists(tenant_id=actor.tenant_id, cert_number=cert_number):
            raise conflict("同一租户内证书编号已存在", certNumber=cert_number)
        entity = QualificationEntity(
            id=new_id(),
            tenant_id=actor.tenant_id,
            name=_text(payload.get("name"), "name"),
            category=_text(payload.get("category"), "category"),
            cert_number=cert_number,
            issuer=_text(payload.get("issuer"), "issuer"),
            valid_from=valid_from,
            expiry_date=expiry_date,
            file=file,
            document_version=_text(payload.get("documentVersion"), "documentVersion"),
            reminder_days=_int_list(payload.get("reminderDays"), "reminderDays"),
            tags=_string_list(payload.get("tags"), "tags"),
            created_at=now,
            updated_at=now,
        )
        saved = self.store.save(entity)
        self.store.save_version(
            QualificationVersionEntity(
                id=new_id(),
                tenant_id=actor.tenant_id,
                qualification_id=saved.id,
                file=file,
                document_version=saved.document_version,
                change_note="初始版本",
                created_by=actor.user_id,
                created_at=now,
            )
        )
        await self._audit(actor, saved, "qualification.created", f"创建资质 {saved.name}")
        await self._notify_if_due(actor, saved)
        return qualification_dict(saved)

    async def get(self, actor: AuthPrincipal, qualification_id: str) -> dict[str, Any]:
        require_internal(actor)
        return qualification_dict(self.store.get(qualification_id, tenant_id=actor.tenant_id))

    async def update(
        self,
        actor: AuthPrincipal,
        qualification_id: str,
        payload: Mapping[str, Any],
        *,
        expected_version: int,
    ) -> dict[str, Any]:
        _require_writer(actor)
        _reject_unknown(payload, _UPDATE_FIELDS)
        entity = self.store.get(qualification_id, tenant_id=actor.tenant_id)
        if expected_version != entity.version:
            raise version_conflict(entity.version)
        field_map = {
            "name": "name",
            "category": "category",
            "certNumber": "cert_number",
            "issuer": "issuer",
            "documentVersion": "document_version",
        }
        for source, target in field_map.items():
            if source in payload:
                setattr(entity, target, _text(payload[source], source))
        if self.store.cert_number_exists(
            tenant_id=actor.tenant_id,
            cert_number=entity.cert_number,
            exclude_id=entity.id,
        ):
            raise conflict("同一租户内证书编号已存在", certNumber=entity.cert_number)
        if "validFrom" in payload:
            entity.valid_from = _optional_date(payload["validFrom"], "validFrom")
        if "expiryDate" in payload:
            entity.expiry_date = _optional_date(payload["expiryDate"], "expiryDate")
        if "reminderDays" in payload:
            entity.reminder_days = _int_list(payload["reminderDays"], "reminderDays")
        if "tags" in payload:
            entity.tags = _string_list(payload["tags"], "tags")
        _validate_dates(entity.valid_from, entity.expiry_date)
        entity.version += 1
        entity.updated_at = _now()
        saved = self.store.save(entity)
        await self._audit(actor, saved, "qualification.updated", f"更新资质 {saved.name}")
        await self._notify_if_due(actor, saved)
        return qualification_dict(saved)

    async def add_version(
        self, actor: AuthPrincipal, qualification_id: str, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        _require_writer(actor)
        _reject_unknown(payload, {"fileId", "documentVersion", "changeNote"})
        entity = self.store.get(qualification_id, tenant_id=actor.tenant_id)
        file = await self._accessible_file(actor, _text(payload.get("fileId"), "fileId"))
        now = _now()
        entity.file = file
        entity.document_version = _text(payload.get("documentVersion"), "documentVersion")
        entity.version += 1
        entity.updated_at = now
        saved = self.store.save(entity)
        self.store.save_version(
            QualificationVersionEntity(
                id=new_id(),
                tenant_id=actor.tenant_id,
                qualification_id=entity.id,
                file=file,
                document_version=entity.document_version,
                change_note=_text(payload.get("changeNote"), "changeNote"),
                created_by=actor.user_id,
                created_at=now,
            )
        )
        await self._audit(actor, saved, "qualification.version_added", f"新增资质版本 {saved.name}")
        return qualification_dict(saved)

    async def delete(self, actor: AuthPrincipal, qualification_id: str, payload: Mapping[str, Any]) -> None:
        _require_admin(actor)
        _reject_unknown(payload, {"reason"})
        entity = self.store.get(qualification_id, tenant_id=actor.tenant_id)
        entity.deleted_at = _now()
        entity.deleted_by = actor.user_id
        entity.deleted_reason = _text(payload.get("reason"), "reason")
        entity.version += 1
        entity.updated_at = entity.deleted_at
        self.store.save(entity)
        await self._audit(actor, entity, "qualification.deleted", f"删除资质 {entity.name}")

    async def import_file(self, actor: AuthPrincipal, payload: Mapping[str, Any]) -> dict[str, Any]:
        _require_writer(actor)
        _reject_unknown(payload, {"fileId"})
        clean_file_id = _text(payload.get("fileId"), "fileId")
        async with self.store.import_lock:
            await self._accessible_file(actor, clean_file_id)
            remembered = self.store.get_import_job(tenant_id=actor.tenant_id, file_id=clean_file_id)
            if remembered is not None:
                return job_dict(remembered)
            idempotency_key = sha256(f"{actor.tenant_id}:{clean_file_id}".encode()).hexdigest()
            job = await self.jobs.enqueue(
                tenant_id=actor.tenant_id,
                job_type="file_import",
                payload={
                    "m5JobType": "qualification.import",
                    "tenantId": actor.tenant_id,
                    "fileId": clean_file_id,
                },
                created_by=actor.user_id,
                idempotency_key=idempotency_key,
            )
            self.store.remember_import_job(
                tenant_id=actor.tenant_id,
                file_id=clean_file_id,
                job=job,
                category=_IMPORT_CATEGORY,
                actor_id=actor.user_id,
                actor_name=actor.name,
                actor_role=actor.role,
            )
            await self.audit.append(
                AuditEventInput(
                    tenant_id=actor.tenant_id,
                    aggregate_type="qualification_import",
                    aggregate_id=job.id,
                    actor_type="user",
                    actor_id=actor.user_id,
                    actor_name=actor.name,
                    action="qualification.import_requested",
                    summary="发起资质批量导入",
                    target_type="file",
                    target_id=clean_file_id,
                )
            )
            return job_dict(job)

    async def apply_import_result(
        self,
        *,
        tenant_id: str,
        job_id: str,
        category: str,
        source_file_id: str,
        rows: list[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        """校验 M7 资质导入结果，并由 M5 一次性写入业务实体与终态。"""
        async with self.store.import_lock:
            binding = self._import_binding(
                tenant_id=tenant_id,
                job_id=job_id,
                category=category,
                source_file_id=source_file_id,
            )
            cached = self.store.get_import_result(binding, outcome="succeeded")
            if cached is not None:
                return cast(list[dict[str, Any]], cached)
            cleaned_rows = self._validate_import_rows(tenant_id=tenant_id, rows=rows)
            actor = AuthPrincipal(
                user_id=binding.actor_id,
                tenant_id=binding.tenant_id,
                name=binding.actor_name,
                role=binding.actor_role,
            )
            source_file = await self._accessible_file(actor, binding.source_file_id)
            now = _now()
            qualifications: list[QualificationEntity] = []
            versions: list[QualificationVersionEntity] = []
            for cleaned in cleaned_rows:
                qualification = QualificationEntity(
                    id=new_id(),
                    tenant_id=binding.tenant_id,
                    name=cleaned["name"],
                    category=cleaned["category"],
                    cert_number=cleaned["cert_number"],
                    issuer=cleaned["issuer"],
                    valid_from=cleaned["valid_from"],
                    expiry_date=cleaned["expiry_date"],
                    file=source_file,
                    document_version=cleaned["document_version"],
                    reminder_days=cleaned["reminder_days"],
                    tags=cleaned["tags"],
                    created_at=now,
                    updated_at=now,
                )
                qualifications.append(qualification)
                versions.append(
                    QualificationVersionEntity(
                        id=new_id(),
                        tenant_id=binding.tenant_id,
                        qualification_id=qualification.id,
                        file=source_file,
                        document_version=qualification.document_version,
                        change_note="批量导入初始版本",
                        created_by=binding.actor_id,
                        created_at=now,
                    )
                )
            response = [qualification_dict(entity) for entity in qualifications]
            await self.audit.append(
                AuditEventInput(
                    tenant_id=binding.tenant_id,
                    aggregate_type="qualification_import",
                    aggregate_id=binding.job_id,
                    actor_type="user",
                    actor_id=binding.actor_id,
                    actor_name=binding.actor_name,
                    action="qualification.import_applied",
                    summary=f"资质批量导入完成，共 {len(response)} 条",
                    target_type="file",
                    target_id=binding.source_file_id,
                )
            )
            self.store.remember_import_result(
                binding,
                outcome="succeeded",
                value=response,
                qualifications=qualifications,
                versions=versions,
            )
            return response

    async def apply_import_failure(
        self,
        *,
        tenant_id: str,
        job_id: str,
        category: str,
        source_file_id: str,
        message: str,
    ) -> dict[str, Any]:
        """记录 M7 资质导入失败终态；失败结果不得写入资质业务实体。"""
        async with self.store.import_lock:
            binding = self._import_binding(
                tenant_id=tenant_id,
                job_id=job_id,
                category=category,
                source_file_id=source_file_id,
            )
            cached = self.store.get_import_result(binding, outcome="failed")
            if cached is not None:
                return cast(dict[str, Any], cached)
            normalized_message = str(message).strip() or "资质导入失败"
            response = {"jobId": binding.job_id, "status": "failed", "message": normalized_message}
            await self.audit.append(
                AuditEventInput(
                    tenant_id=binding.tenant_id,
                    aggregate_type="qualification_import",
                    aggregate_id=binding.job_id,
                    actor_type="user",
                    actor_id=binding.actor_id,
                    actor_name=binding.actor_name,
                    action="qualification.import_failed",
                    summary=normalized_message,
                    target_type="file",
                    target_id=binding.source_file_id,
                )
            )
            await self.notifications.notify(
                NotificationInput(
                    tenant_id=binding.tenant_id,
                    title="资质批量导入失败",
                    content=normalized_message,
                    type="task",
                    user_id=binding.actor_id,
                    resource_type="file",
                    resource_id=binding.source_file_id,
                )
            )
            self.store.remember_import_result(binding, outcome="failed", value=response)
            return response

    def _import_binding(
        self,
        *,
        tenant_id: str,
        job_id: str,
        category: str,
        source_file_id: str,
    ) -> QualificationImportBindingEntity:
        binding = self.store.get_import_binding(job_id, tenant_id=tenant_id)
        if binding.category != category or binding.source_file_id != source_file_id:
            raise conflict(
                "资质导入结果与原始任务不匹配",
                jobId=job_id,
                category=category,
                sourceFileId=source_file_id,
            )
        return binding

    def _validate_import_rows(
        self,
        *,
        tenant_id: str,
        rows: Any,
    ) -> list[dict[str, Any]]:
        if not isinstance(rows, list) or not rows:
            raise validation_error(
                "资质导入结果 rows 必须为非空数组",
                field_errors=[{"field": "rows", "code": "REQUIRED", "message": "必须为非空数组"}],
            )
        cleaned_rows: list[dict[str, Any]] = []
        seen_cert_numbers: set[str] = set()
        for row_number, raw in enumerate(rows, start=1):
            if not isinstance(raw, Mapping) or any(not isinstance(key, str) for key in raw):
                raise validation_error(
                    f"导入第 {row_number} 行必须为对象",
                    field_errors=[{"field": f"rows[{row_number}]", "code": "TYPE", "message": "必须为对象"}],
                )
            row = dict(raw)
            _reject_unknown(row, _IMPORT_ROW_FIELDS)
            cert_number = _import_text(row, "certNumber", row_number)
            cert_key = cert_number.casefold()
            if cert_key in seen_cert_numbers:
                raise validation_error(
                    "导入批次内证书编号重复",
                    field_errors=[
                        {
                            "field": f"rows[{row_number}].certNumber",
                            "code": "DUPLICATE",
                            "message": cert_number,
                        }
                    ],
                )
            if self.store.cert_number_exists(tenant_id=tenant_id, cert_number=cert_number):
                raise conflict("同一租户内证书编号已存在", certNumber=cert_number)
            valid_from = _optional_date(row.get("validFrom"), f"rows[{row_number}].validFrom")
            expiry_date = _optional_date(row.get("expiryDate"), f"rows[{row_number}].expiryDate")
            _validate_dates(valid_from, expiry_date)
            reminder_days = _int_list(row.get("reminderDays"), f"rows[{row_number}].reminderDays")
            cleaned_rows.append(
                {
                    "name": _import_text(row, "name", row_number),
                    "category": _import_text(row, "category", row_number),
                    "cert_number": cert_number,
                    "issuer": _import_text(row, "issuer", row_number),
                    "valid_from": valid_from,
                    "expiry_date": expiry_date,
                    "document_version": _import_text(row, "documentVersion", row_number),
                    "reminder_days": reminder_days,
                    "tags": _import_tags(row, row_number),
                }
            )
            seen_cert_numbers.add(cert_key)
        return cleaned_rows

    async def import_template(self, actor: AuthPrincipal) -> tuple[bytes, str]:
        require_internal(actor)
        content = build_xlsx(
            [
                [
                    "name",
                    "category",
                    "certNumber",
                    "issuer",
                    "validFrom",
                    "expiryDate",
                    "documentVersion",
                    "reminderDays",
                    "tags",
                ],
                [
                    "示例资质",
                    "企业资质",
                    "CERT-001",
                    "示例发证机构",
                    "2026-01-01",
                    "2027-01-01",
                    "1.0",
                    "30,60,90",
                    "示例,投标",
                ],
            ],
            sheet_name="资质导入模板",
        )
        return content, sha256(content).hexdigest()

    async def download(self, actor: AuthPrincipal, qualification_id: str) -> tuple[str, str, str, str]:
        require_internal(actor)
        entity = self.store.get(qualification_id, tenant_id=actor.tenant_id)
        file = await self._accessible_file(actor, entity.file.id)
        url = await self.files.get_download_url(tenant_id=actor.tenant_id, file_id=file.id, expires_minutes=60)
        if not url:
            raise not_found("资质文件暂不可下载", qualificationId=qualification_id)
        return url, file.file_name, file.sha256, file.mime_type

    async def _accessible_file(self, actor: AuthPrincipal, file_id: str) -> FileRefSnapshot:
        try:
            file = await self.files.assert_accessible(
                tenant_id=actor.tenant_id,
                file_id=file_id,
                actor_id=actor.user_id,
                purpose="qualification",
            )
        except KeyError as exc:
            raise not_found("文件不存在", fileId=file_id) from exc
        _require_clean(file)
        return file

    async def _audit(self, actor: AuthPrincipal, entity: QualificationEntity, action: str, summary: str) -> None:
        await self.audit.append(
            AuditEventInput(
                tenant_id=actor.tenant_id,
                aggregate_type="qualification",
                aggregate_id=entity.id,
                actor_type="user",
                actor_id=actor.user_id,
                actor_name=actor.name,
                action=action,
                summary=summary,
            )
        )

    async def _notify_if_due(self, actor: AuthPrincipal, entity: QualificationEntity) -> None:
        status = qualification_status(entity)
        if status == "valid" or entity.expiry_date is None:
            return
        days_left = (entity.expiry_date - date.today()).days
        content = "资质已过期" if days_left < 0 else f"资质将在 {days_left} 天后到期"
        await self.notifications.notify(
            NotificationInput(
                tenant_id=actor.tenant_id,
                title=f"资质有效期提醒：{entity.name}",
                content=content,
                type="task",
                user_id=actor.user_id,
                resource_type="qualification",
                resource_id=entity.id,
            )
        )
