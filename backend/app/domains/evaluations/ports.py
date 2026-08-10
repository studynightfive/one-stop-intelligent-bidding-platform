"""跨成员端口协议：M6 稳定形状；真实实现由 M4/M5 经 adapters 注入。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Protocol, runtime_checkable

Role = Literal["admin", "project_lead", "member", "reviewer"]


@dataclass(frozen=True, slots=True)
class AuthPrincipal:
    """内部用户鉴权上下文（由 M4 AuthenticatedUser / AuthContext 注入）。"""

    user_id: str
    tenant_id: str
    name: str
    role: Role
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PortalPrincipal:
    """供应商门户会话主体（由 Portal Token 解析得到）。"""

    supplier_id: str
    evaluation_id: str
    tenant_id: str
    name: str


@dataclass(frozen=True, slots=True)
class FileRefSnapshot:
    id: str
    file_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    scan_status: Literal["pending", "clean", "infected", "failed"]
    created_at: datetime
    preview_url: str | None = None
    download_url: str | None = None


@dataclass(frozen=True, slots=True)
class JobRefSnapshot:
    id: str
    type: str
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    progress_percent: int
    created_at: datetime
    current_step: str | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class BidMaterialSnapshot:
    name: str
    category: Literal["qualification", "commercial", "technical"]
    required: bool
    allowed_mime_types: tuple[str, ...]
    max_size_bytes: int
    sort_order: int


@dataclass(frozen=True, slots=True)
class BidTaskSnapshot:
    """M5 BidTaskSnapshotPort 返回的只读快照。"""

    id: str
    tenant_id: str
    project_name: str
    tender_no: str
    tender_entity: str
    deadline: datetime
    budget_amount: Decimal | None = None
    materials: tuple[BidMaterialSnapshot, ...] = ()
    scoring_hints: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class AuditEventInput:
    """对齐 M4 AuditService.log / log_user_action 所需字段。"""

    tenant_id: str
    aggregate_type: str
    aggregate_id: str
    actor_type: Literal["user", "supplier", "system"]
    actor_id: str | None
    actor_name: str
    action: str
    summary: str
    target_type: str | None = None
    target_id: str | None = None
    changes: tuple[dict[str, Any], ...] = ()
    request_id: str = ""
    ip_address: str | None = None


@dataclass(frozen=True, slots=True)
class NotificationInput:
    """对齐 M4 NotificationService.create_notification；email 为门户扩展（M4 当前按 user_id）。"""

    tenant_id: str
    title: str
    content: str
    type: str = "task"
    user_id: str | None = None
    email: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None


@runtime_checkable
class BidTaskSnapshotPort(Protocol):
    async def get_snapshot(self, *, tenant_id: str, bid_task_id: str) -> BidTaskSnapshot: ...


@runtime_checkable
class FileServicePort(Protocol):
    async def get_file(self, *, tenant_id: str, file_id: str) -> FileRefSnapshot: ...

    async def assert_accessible(
        self, *, tenant_id: str, file_id: str, actor_id: str, purpose: str
    ) -> FileRefSnapshot: ...

    async def get_download_url(self, *, tenant_id: str, file_id: str, expires_minutes: int = 60) -> str | None: ...


@runtime_checkable
class JobDispatcherPort(Protocol):
    async def enqueue(
        self,
        *,
        tenant_id: str,
        job_type: str,
        payload: dict[str, Any],
        created_by: str,
        project_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> JobRefSnapshot: ...


@runtime_checkable
class NotificationServicePort(Protocol):
    async def notify(self, event: NotificationInput) -> None: ...


@runtime_checkable
class AuditServicePort(Protocol):
    async def append(self, event: AuditEventInput) -> None: ...


@dataclass
class RecordingPorts:
    """测试用端口集合：记录调用，不触达真实基础设施。"""

    audits: list[AuditEventInput] = field(default_factory=list)
    notifications: list[NotificationInput] = field(default_factory=list)
    jobs: list[JobRefSnapshot] = field(default_factory=list)
    files: dict[str, FileRefSnapshot] = field(default_factory=dict)
    bid_snapshots: dict[str, BidTaskSnapshot] = field(default_factory=dict)
    download_urls: dict[str, str] = field(default_factory=dict)

    async def get_snapshot(self, *, tenant_id: str, bid_task_id: str) -> BidTaskSnapshot:
        key = f"{tenant_id}:{bid_task_id}"
        if key not in self.bid_snapshots:
            raise KeyError(bid_task_id)
        snapshot = self.bid_snapshots[key]
        if snapshot.tenant_id != tenant_id:
            raise KeyError(bid_task_id)
        return snapshot

    async def get_file(self, *, tenant_id: str, file_id: str) -> FileRefSnapshot:
        _ = tenant_id
        if file_id not in self.files:
            raise KeyError(file_id)
        return self.files[file_id]

    async def assert_accessible(self, *, tenant_id: str, file_id: str, actor_id: str, purpose: str) -> FileRefSnapshot:
        _ = actor_id, purpose
        return await self.get_file(tenant_id=tenant_id, file_id=file_id)

    async def get_download_url(self, *, tenant_id: str, file_id: str, expires_minutes: int = 60) -> str | None:
        _ = tenant_id, expires_minutes
        return self.download_urls.get(file_id)

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
        from datetime import UTC

        from app.domains.evaluations.ids import new_id

        _ = tenant_id, payload, created_by, project_id, idempotency_key
        job = JobRefSnapshot(
            id=new_id(),
            type=job_type,
            status="queued",
            progress_percent=0,
            created_at=datetime.now(UTC),
            current_step="queued",
        )
        self.jobs.append(job)
        return job

    async def notify(self, event: NotificationInput) -> None:
        self.notifications.append(event)

    async def append(self, event: AuditEventInput) -> None:
        self.audits.append(event)
