"""M6 端口与已合并 M4 服务签名的回归测试."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.domains.evaluations.m4_adapters import (
    M4AuditAdapter,
    M4FileServiceAdapter,
    M4JobDispatcherAdapter,
    M4NotificationAdapter,
    build_m4_ports,
)
from app.domains.evaluations.ports import AuditEventInput, NotificationInput


class _Dispatcher:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def dispatch(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            id=uuid4(),
            status=SimpleNamespace(value="running"),
            progress_percent=35,
            current_step="分析中",
            created_at=datetime.now(UTC),
        )


class _NotificationService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create_notification(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _AuditService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def log(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _FileService:
    def __init__(self, file_obj: object | None) -> None:
        self.file_obj = file_obj
        self.fail_urls = False
        self.calls: list[tuple[str, UUID, UUID]] = []

    async def get_file(self, file_id: UUID, tenant_id: UUID):
        self.calls.append(("get", file_id, tenant_id))
        return self.file_obj

    async def get_preview_url(self, file_id: UUID, tenant_id: UUID) -> str:
        self.calls.append(("preview", file_id, tenant_id))
        if self.fail_urls:
            raise RuntimeError("preview unavailable")
        return "https://files.example.test/preview"

    async def get_download_url(self, file_id: UUID, tenant_id: UUID) -> str:
        self.calls.append(("download", file_id, tenant_id))
        if self.fail_urls:
            raise RuntimeError("download unavailable")
        return "https://files.example.test/download"


@pytest.mark.asyncio
async def test_job_notification_and_audit_adapters() -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    aggregate_id = uuid4()
    target_id = uuid4()

    dispatcher = _Dispatcher()
    job_adapter = M4JobDispatcherAdapter(dispatcher)
    job = await job_adapter.enqueue(
        tenant_id=str(tenant_id),
        job_type="evaluation.report_generate",
        payload={"evaluationId": str(aggregate_id)},
        created_by=str(user_id),
        idempotency_key="job-test",
    )
    assert job.status == "running"
    assert dispatcher.calls[0]["tenant_id"] == tenant_id

    notification_adapter = M4NotificationAdapter(object())
    notification_service = _NotificationService()
    notification_adapter._service = notification_service
    await notification_adapter.notify(NotificationInput(tenant_id=str(tenant_id), title="跳过", content="无内部用户"))
    assert notification_service.calls == []
    await notification_adapter.notify(
        NotificationInput(
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            title="评标任务",
            content="待处理",
            type="unknown-type",
            resource_type="evaluation",
            resource_id=str(aggregate_id),
        )
    )
    assert notification_service.calls[0]["user_id"] == user_id

    audit_adapter = M4AuditAdapter(object())
    audit_service = _AuditService()
    audit_adapter._service = audit_service
    await audit_adapter.append(
        AuditEventInput(
            tenant_id=str(tenant_id),
            aggregate_type="evaluation",
            aggregate_id=str(aggregate_id),
            actor_type="user",
            actor_id=str(user_id),
            actor_name="负责人",
            action="evaluation.updated",
            summary="更新评标",
            target_type="supplier",
            target_id=str(target_id),
            changes=({"field": "status", "oldValue": "draft", "newValue": "collecting"},),
            request_id="request-test",
        )
    )
    assert audit_service.calls[0]["target_id"] == target_id
    assert audit_service.calls[0]["changes"]["targetType"] == "supplier"


@pytest.mark.asyncio
async def test_file_adapter_enforces_tenant_signature_and_handles_url_failures() -> None:
    tenant_id = uuid4()
    file_id = uuid4()
    file_obj = SimpleNamespace(
        id=file_id,
        tenant_id=tenant_id,
        file_name="proposal.pdf",
        mime_type="application/pdf",
        size_bytes=123,
        sha256="c" * 64,
        scan_status=SimpleNamespace(value="clean"),
        created_at=datetime.now(UTC),
    )
    service = _FileService(file_obj)
    adapter = M4FileServiceAdapter(object())
    adapter._service = service

    snapshot = await adapter.get_file(tenant_id=str(tenant_id), file_id=str(file_id))
    assert snapshot.scan_status == "clean"
    assert snapshot.preview_url and snapshot.download_url
    assert await adapter.get_download_url(tenant_id=str(tenant_id), file_id=str(file_id))
    assert all(call[2] == tenant_id for call in service.calls)

    file_obj.scan_status = "unexpected"
    service.fail_urls = True
    snapshot_without_urls = await adapter.get_file(tenant_id=str(tenant_id), file_id=str(file_id))
    assert snapshot_without_urls.scan_status == "pending"
    assert snapshot_without_urls.preview_url is None
    assert snapshot_without_urls.download_url is None

    service.file_obj = None
    with pytest.raises(KeyError):
        await adapter.get_file(tenant_id=str(tenant_id), file_id=str(file_id))


def test_build_m4_ports_uses_merged_platform_services() -> None:
    jobs, notifications, audit, files = build_m4_ports(object())
    assert isinstance(jobs, M4JobDispatcherAdapter)
    assert isinstance(notifications, M4NotificationAdapter)
    assert isinstance(audit, M4AuditAdapter)
    assert isinstance(files, M4FileServiceAdapter)
