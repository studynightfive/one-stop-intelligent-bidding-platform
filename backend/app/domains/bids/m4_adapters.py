"""M5 adapters for the stable M4 infrastructure services and the M6 snapshot port."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from app.domains.bids.errors import DomainError
from app.domains.bids.ports import (
    AuditServicePort,
    BidMaterialSnapshot,
    BidTaskSnapshot,
    BidTaskSnapshotPort,
    FileServicePort,
    JobDispatcherPort,
    JobRefSnapshot,
    NotificationServicePort,
)
from app.domains.bids.store import BidStore
from app.domains.evaluations.m4_adapters import (
    M4AuditAdapter,
    M4NotificationAdapter,
)

M5_JOB_TYPE_TO_M4: dict[str, str] = {
    "ai_analysis": "ai_analysis",
    "document_generation": "document_generation",
    "file_import": "file_import",
    "export": "export",
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

_DEFAULT_MIME_TYPES = (
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/jpeg",
    "image/png",
)


def _as_uuid(value: str) -> UUID:
    return UUID(str(value))


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


class M5JobDispatcherAdapter:
    """Translate M5's four infrastructure job categories to M4 ``JobType``."""

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

        m4_type_raw = M5_JOB_TYPE_TO_M4.get(job_type)
        if m4_type_raw is None:
            raise ValueError(f"Unsupported M5 job type: {job_type}")
        job = await self._dispatcher.dispatch(
            user_id=_as_uuid(created_by),
            tenant_id=_as_uuid(tenant_id),
            job_type=JobType(m4_type_raw),
            input_data={**payload, "idempotencyKey": idempotency_key},
            project_id=_as_uuid(project_id) if project_id else None,
        )
        status = M4_STATUS_TO_CONTRACT.get(_enum_value(job.status).lower(), "queued")
        return JobRefSnapshot(
            id=str(job.id),
            type=job_type,
            status=status,  # type: ignore[arg-type]
            progress_percent=int(getattr(job, "progress_percent", 0) or 0),
            created_at=getattr(job, "created_at", None) or datetime.now(UTC),
            current_step=getattr(job, "current_step", None),
        )


class M5BidTaskSnapshotAdapter(BidTaskSnapshotPort):
    """Expose a tenant-scoped, immutable M5 bid task snapshot to M6."""

    def __init__(self, store: BidStore) -> None:
        self._store = store

    async def get_snapshot(self, *, tenant_id: str, bid_task_id: str) -> BidTaskSnapshot:
        try:
            task = self._store.get_task(bid_task_id, tenant_id=tenant_id)
        except DomainError as exc:
            raise KeyError(bid_task_id) from exc

        budget_amount = _budget_amount(task.requirements.project_info if task.requirements else {})
        materials = tuple(
            BidMaterialSnapshot(
                name=item.name,
                category=item.category,  # type: ignore[arg-type]
                required=item.required,
                allowed_mime_types=_DEFAULT_MIME_TYPES,
                max_size_bytes=50 * 1024 * 1024,
                sort_order=item.sort_order,
            )
            for item in task.materials
        )
        scoring_hints = tuple(dict(item) for item in (task.requirements.scoring_items if task.requirements else []))
        return BidTaskSnapshot(
            id=task.id,
            tenant_id=task.tenant_id,
            project_name=task.project_name,
            tender_no=task.tender_no,
            tender_entity=task.tender_entity,
            deadline=task.deadline,
            budget_amount=budget_amount,
            materials=materials,
            scoring_hints=scoring_hints,
        )


def _budget_amount(project_info: dict[str, str]) -> Decimal | None:
    raw = project_info.get("budgetAmount") or project_info.get("budget_amount")
    if raw in (None, ""):
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None


def build_m4_ports(
    db: Any,
    *,
    files: FileServicePort,
) -> tuple[JobDispatcherPort, NotificationServicePort, AuditServicePort, FileServicePort]:
    """Build M5 ports while requiring an actor- and purpose-aware file port.

    M4's current generic file adapter only enforces tenant isolation and therefore
    cannot satisfy M5's stronger ``assert_accessible`` contract.  L0 must inject
    the authorized M4 file capability explicitly instead of receiving an unsafe
    fallback here.
    """
    if not isinstance(files, FileServicePort):
        raise TypeError("M5 requires an explicit authorized FileServicePort")
    return (
        M5JobDispatcherAdapter(),
        M4NotificationAdapter(db),
        M4AuditAdapter(db),
        files,
    )
