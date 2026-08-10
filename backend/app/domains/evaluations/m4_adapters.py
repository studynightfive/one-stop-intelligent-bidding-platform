"""M4 真实 Service -> M6 Port 适配器。

依据仓库根目录/只读分支中的 M4_SERVICE_USAGE.md。
M4 未合入当前工作树时，import 会失败；测试请继续用 RecordingPorts。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from app.domains.evaluations.ports import (
    AuditEventInput,
    AuditEventSnapshot,
    AuditServicePort,
    FileRefSnapshot,
    FileServicePort,
    JobDispatcherPort,
    JobRefSnapshot,
    NotificationInput,
    NotificationServicePort,
)

# 总提示词场景名 -> M4 JobType 字符串（再由适配器转枚举）
M6_JOB_TYPE_TO_M4: dict[str, str] = {
    "evaluation.material_check": "ai_analysis",
    "evaluation.risk_check": "ai_analysis",
    "evaluation.ai_scoring": "ai_analysis",
    "evaluation.report_generate": "document_generation",
    "evaluation_check": "ai_analysis",
    "risk_check": "ai_analysis",
    "evaluation_score": "ai_analysis",
    "report_generate": "document_generation",
}

M4_STATUS_TO_CONTRACT: dict[str, str] = {
    "pending": "queued",
    "queued": "queued",
    "running": "running",
    "succeeded": "succeeded",
    "success": "succeeded",
    "completed": "succeeded",
    "failed": "failed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}


def _as_uuid(value: str) -> UUID:
    return UUID(str(value))


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


class M4JobDispatcherAdapter:
    """包装 `job_dispatcher.dispatch`。"""

    def __init__(self, dispatcher: Any | None = None) -> None:
        if dispatcher is not None:
            self._dispatcher = dispatcher
            return
        from app.domains.jobs.services.job_dispatcher import job_dispatcher

        self._dispatcher = job_dispatcher

    async def enqueue(
        self,
        *,
        tenant_id: str,
        job_type: str,
        payload: dict[str, Any],
        created_by: str,
        project_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> JobRefSnapshot:
        from app.domains.jobs.models.job import JobType

        m4_type_raw = M6_JOB_TYPE_TO_M4.get(job_type, "other")
        try:
            m4_type = JobType(m4_type_raw)
        except ValueError:
            m4_type = JobType.OTHER

        input_data = {
            **payload,
            "m6JobType": job_type,
            "idempotencyKey": idempotency_key,
        }
        job = await self._dispatcher.dispatch(
            user_id=_as_uuid(created_by),
            tenant_id=_as_uuid(tenant_id),
            job_type=m4_type,
            input_data=input_data,
            project_id=_as_uuid(project_id) if project_id else None,
        )
        status = M4_STATUS_TO_CONTRACT.get(_enum_value(job.status).lower(), "queued")
        created_at = getattr(job, "created_at", None) or datetime.now(UTC)
        return JobRefSnapshot(
            id=str(job.id),
            type=job_type,
            status=status,  # type: ignore[arg-type]
            progress_percent=int(getattr(job, "progress_percent", 0) or 0),
            created_at=created_at,
            current_step=getattr(job, "current_step", None),
            result=getattr(job, "result", None),
            error=getattr(job, "error", None),
        )


class M4NotificationAdapter:
    """包装 NotificationService；无内部 user_id 时跳过（供应商邮件待 M4/邮件通道）。"""

    def __init__(self, db: Any) -> None:
        from app.domains.notifications.services.notification_service import NotificationService

        self._service = NotificationService(db)

    async def notify(self, event: NotificationInput) -> None:
        if not event.user_id:
            return
        from app.domains.notifications.models.notification import NotificationType

        try:
            ntype = NotificationType(event.type)
        except ValueError:
            ntype = NotificationType.TASK
        await self._service.create_notification(
            user_id=_as_uuid(event.user_id),
            tenant_id=_as_uuid(event.tenant_id),
            notification_type=ntype,
            title=event.title,
            content=event.content,
            resource_type=event.resource_type,
            resource_id=_as_uuid(event.resource_id) if event.resource_id else None,
        )


class M4AuditAdapter:
    """包装 AuditService.log。"""

    def __init__(self, db: Any) -> None:
        from app.domains.audit.services.audit_service import AuditService

        self._service = AuditService(db)

    async def append(self, event: AuditEventInput) -> None:
        from app.domains.audit.models.audit_event import ActorType

        actor_type = ActorType(event.actor_type)
        changes: dict[str, Any] | None = None
        if event.changes:
            changes = {"items": list(event.changes)}
            if event.target_type:
                changes["targetType"] = event.target_type
            if event.target_id:
                changes["targetId"] = event.target_id
        await self._service.log(
            tenant_id=_as_uuid(event.tenant_id),
            aggregate_type=event.aggregate_type,
            aggregate_id=_as_uuid(event.aggregate_id),
            actor_type=actor_type,
            actor_id=_as_uuid(event.actor_id) if event.actor_id else None,
            actor_name=event.actor_name,
            action=event.action,
            summary=event.summary,
            target_type=event.target_type,
            target_id=_as_uuid(event.target_id) if event.target_id else None,
            changes=changes,
            request_id=event.request_id,
            ip_address=event.ip_address,
        )

    async def list_events(
        self,
        *,
        tenant_id: str,
        aggregate_type: str,
        aggregate_id: str,
        actor: str | None = None,
        action: str | None = None,
        resource: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AuditEventSnapshot], int]:
        actor_id: UUID | None = None
        actor_name_filter: str | None = None
        if actor:
            try:
                actor_id = _as_uuid(actor)
            except ValueError:
                actor_name_filter = actor.casefold()

        query_limit = 10_000 if actor_name_filter else limit
        query_offset = 0 if actor_name_filter else offset
        events, total = await self._service.list_events(
            tenant_id=_as_uuid(tenant_id),
            aggregate_type=aggregate_type,
            aggregate_id=_as_uuid(aggregate_id),
            actor_id=actor_id,
            action=action,
            target_type=resource,
            start_date=date_from,
            end_date=date_to,
            limit=query_limit,
            offset=query_offset,
        )
        if actor_name_filter:
            events = [event for event in events if actor_name_filter in event.actor_name.casefold()]
            total = len(events)
            events = events[offset : offset + limit]

        return [self._snapshot(event) for event in events], total

    @staticmethod
    def _snapshot(event: Any) -> AuditEventSnapshot:
        raw_changes = getattr(event, "changes", None)
        changes: tuple[dict[str, Any], ...] = ()
        if isinstance(raw_changes, dict):
            raw_items = raw_changes.get("items")
            if isinstance(raw_items, list):
                changes = tuple(item for item in raw_items if isinstance(item, dict))

        actor_type = _enum_value(event.actor_type)
        if actor_type not in {"user", "supplier", "system"}:
            actor_type = "system"
        return AuditEventSnapshot(
            id=str(event.id),
            tenant_id=str(event.tenant_id),
            aggregate_type=str(event.aggregate_type),
            aggregate_id=str(event.aggregate_id),
            actor_type=cast(Any, actor_type),
            actor_id=str(event.actor_id) if event.actor_id else None,
            actor_name=str(event.actor_name),
            action=str(event.action),
            summary=str(event.summary),
            request_id=str(event.request_id),
            created_at=event.created_at,
            target_type=getattr(event, "target_type", None),
            target_id=str(event.target_id) if getattr(event, "target_id", None) else None,
            changes=changes,
            ip_address=getattr(event, "ip_address", None),
        )


class M4FileServiceAdapter:
    """包装 FileService：元数据读取 + 签名下载 URL。"""

    def __init__(self, db: Any) -> None:
        from app.domains.files.services.file_service import FileService

        self._service = FileService(db)
        self._db = db

    async def get_file(self, *, tenant_id: str, file_id: str) -> FileRefSnapshot:
        file_obj = await self._load_file(tenant_id=tenant_id, file_id=file_id)
        return await self._to_snapshot(file_obj, tenant_id=tenant_id)

    async def assert_accessible(self, *, tenant_id: str, file_id: str, actor_id: str, purpose: str) -> FileRefSnapshot:
        _ = actor_id, purpose
        return await self.get_file(tenant_id=tenant_id, file_id=file_id)

    async def get_download_url(
        self,
        *,
        tenant_id: str,
        file_id: str,
        expires_minutes: int = 60,
    ) -> str | None:
        _ = expires_minutes  # M4 当前统一签发一小时有效期。
        return await self._service.get_download_url(_as_uuid(file_id), _as_uuid(tenant_id))

    async def _load_file(self, *, tenant_id: str, file_id: str) -> Any:
        file_obj = await self._service.get_file(_as_uuid(file_id), _as_uuid(tenant_id))
        if file_obj is None:
            raise KeyError(file_id)
        return file_obj

    async def _to_snapshot(self, file_obj: Any, *, tenant_id: str) -> FileRefSnapshot:
        scan = _enum_value(getattr(file_obj, "scan_status", "pending")).lower()
        if scan not in {"pending", "clean", "infected", "failed"}:
            scan = "pending"
        preview = None
        download = None
        try:
            preview = await self._service.get_preview_url(file_obj.id, _as_uuid(tenant_id))
        except Exception:
            preview = None
        try:
            download = await self._service.get_download_url(file_obj.id, _as_uuid(tenant_id))
        except Exception:
            download = None
        return FileRefSnapshot(
            id=str(file_obj.id),
            file_name=str(getattr(file_obj, "file_name", getattr(file_obj, "filename", "file"))),
            mime_type=str(
                getattr(file_obj, "content_type", getattr(file_obj, "mime_type", "application/octet-stream"))
            ),
            size_bytes=int(getattr(file_obj, "file_size", getattr(file_obj, "size_bytes", 0)) or 0),
            sha256=str(getattr(file_obj, "sha256_hash", getattr(file_obj, "sha256", "")) or ("0" * 64)),
            scan_status=scan,  # type: ignore[arg-type]
            created_at=getattr(file_obj, "created_at", datetime.now(UTC)),
            preview_url=preview,
            download_url=download,
        )


def build_m4_ports(db: Any) -> tuple[JobDispatcherPort, NotificationServicePort, AuditServicePort, FileServicePort]:
    """供 L0/集成层一次性装配。"""
    return (
        M4JobDispatcherAdapter(),
        M4NotificationAdapter(db),
        M4AuditAdapter(db),
        M4FileServiceAdapter(db),
    )
