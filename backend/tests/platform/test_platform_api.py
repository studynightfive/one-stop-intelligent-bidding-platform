"""公共平台 HTTP 适配层测试。"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, Request

from app.core.errors import FileRejectedError, ForbiddenError, NotFoundError, ValidationError
from app.domains.audit.api import export_audit_events, list_audit_events
from app.domains.auth.api import auth as auth_api
from app.domains.auth.schemas.auth import LoginRequest
from app.domains.files.api import files as files_api
from app.domains.files.schemas.file import CompleteUploadRequest
from app.domains.jobs.api import jobs as jobs_api
from app.domains.jobs.models.job import JobStatus, JobType
from app.domains.notifications import api as notifications_api
from app.domains.notifications.models.notification import NotificationType
from app.domains.search.api import global_search
from app.domains.settings import api as settings_api
from app.domains.settings.services.settings_service import SettingsService


def _current_user() -> dict[str, str]:
    return {"id": str(uuid4()), "tenant_id": str(uuid4()), "role": "admin"}


@pytest.mark.asyncio
async def test_login_api_returns_contract_envelope_and_refresh_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(UTC)
    user = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        email="admin@example.com",
        name="Admin",
        phone=None,
        role=SimpleNamespace(value="admin"),
        department="PMO",
        status=SimpleNamespace(value="active"),
        last_login_at=now,
        created_at=now,
        updated_at=now,
    )
    service = SimpleNamespace(
        authenticate=AsyncMock(return_value=user),
        create_tokens=AsyncMock(
            return_value={
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "expires_in": 900,
            }
        ),
    )
    monkeypatch.setattr(auth_api, "AuthService", lambda _db: service)
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "headers": [(b"x-request-id", b"auth-request")],
        }
    )

    response = await auth_api.login(
        LoginRequest(email="admin@example.com", password="DemoAdmin123!"),
        request,
        object(),  # type: ignore[arg-type]
    )
    body = json.loads(response.body)
    assert body["success"] is True
    assert body["requestId"] == "auth-request"
    assert body["data"]["accessToken"] == "access-token"
    assert body["data"]["user"]["tenantId"] == str(user.tenant_id)
    assert body["data"]["permissions"] == ["*"]
    assert "refresh_token=refresh-token" in response.headers["set-cookie"]


def _session() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        file_name="proposal.pdf",
        size_bytes=10,
        part_size_bytes=10,
        total_parts=1,
        uploaded_parts=[{"part_number": 1, "etag": "etag"}],
        status=SimpleNamespace(value="uploading"),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


def _file() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        file_name="proposal.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        sha256="hash",
        scan_status=SimpleNamespace(value="clean"),
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_file_api_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    service = SimpleNamespace(
        create_upload_session=AsyncMock(return_value=_session()),
        get_upload_session=AsyncMock(return_value=_session()),
        record_uploaded_part=AsyncMock(),
        complete_upload=AsyncMock(return_value=_file()),
        cancel_upload_session=AsyncMock(),
        get_preview_url=AsyncMock(return_value="https://preview"),
        get_download_url=AsyncMock(return_value="https://download"),
    )
    monkeypatch.setattr(files_api, "FileService", lambda _db: service)
    current_user = _current_user()
    request = {
        "file_name": "proposal.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 10,
        "sha256": "hash",
    }

    created = await files_api.create_upload_session(request, current_user, object())
    assert created.file_name == "proposal.pdf"
    assert (await files_api.get_upload_session(created.id, current_user, object())).id
    uploaded = await files_api.upload_part(created.id, 1, current_user, object(), None)  # type: ignore[arg-type]
    assert uploaded.part_number == 1
    completed = await files_api.complete_upload(
        created.id,
        CompleteUploadRequest(parts=[{"part_number": 1, "etag": "etag"}]),
        current_user,
        object(),
    )
    assert completed.file_name == "proposal.pdf"
    await files_api.cancel_upload(created.id, current_user, object())
    assert await files_api.preview_file(completed.id, current_user, object()) == {"preview_url": "https://preview"}
    assert await files_api.download_file(completed.id, current_user, object()) == {"download_url": "https://download"}


@pytest.mark.asyncio
async def test_file_api_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    service = SimpleNamespace(
        get_upload_session=AsyncMock(return_value=None),
        complete_upload=AsyncMock(side_effect=FileRejectedError()),
        get_preview_url=AsyncMock(side_effect=NotFoundError()),
        get_download_url=AsyncMock(side_effect=NotFoundError()),
    )
    monkeypatch.setattr(files_api, "FileService", lambda _db: service)
    current_user = _current_user()
    identifier = uuid4()
    with pytest.raises(HTTPException) as missing:
        await files_api.get_upload_session(identifier, current_user, object())
    assert missing.value.status_code == 404
    with pytest.raises(HTTPException) as rejected:
        await files_api.complete_upload(identifier, CompleteUploadRequest(parts=[]), current_user, object())
    assert rejected.value.status_code == 400
    with pytest.raises(HTTPException):
        await files_api.preview_file(identifier, current_user, object())
    with pytest.raises(HTTPException):
        await files_api.download_file(identifier, current_user, object())


def _job() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        type=JobType.OTHER,
        status=JobStatus.RUNNING,
        progress_percent=50,
        current_step="processing",
        result=None,
        error=None,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_jobs_api(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _job()
    service = SimpleNamespace(
        get_job_for_user=AsyncMock(return_value=job),
        cancel_job=AsyncMock(return_value=SimpleNamespace(id=job.id, status=JobStatus.CANCELLED)),
    )
    monkeypatch.setattr(jobs_api, "JobService", lambda _db: service)
    current_user = _current_user()
    assert (await jobs_api.get_job(job.id, current_user, object())).progress_percent == 50
    assert (await jobs_api.cancel_job(job.id, current_user, object())).status == "cancelled"

    for error, expected in ((NotFoundError(), 404), (ForbiddenError(), 403)):
        service.get_job_for_user.side_effect = error
        with pytest.raises(HTTPException) as raised:
            await jobs_api.get_job(job.id, current_user, object())
        assert raised.value.status_code == expected

    for error, expected in ((NotFoundError(), 404), (ForbiddenError(), 403), (ValidationError(), 400)):
        service.get_job_for_user.side_effect = None
        service.get_job_for_user.return_value = job
        service.cancel_job.side_effect = error
        with pytest.raises(HTTPException) as raised:
            await jobs_api.cancel_job(job.id, current_user, object())
        assert raised.value.status_code == expected


@pytest.mark.asyncio
async def test_notifications_api(monkeypatch: pytest.MonkeyPatch) -> None:
    notification = SimpleNamespace(
        id=uuid4(),
        type=NotificationType.SYSTEM,
        title="title",
        content="content",
        is_read=False,
        resource_type=None,
        resource_id=None,
        created_at=datetime.now(UTC),
    )
    service = SimpleNamespace(
        list_notifications=AsyncMock(return_value=([notification], 1, 1)),
        mark_as_read=AsyncMock(return_value=notification),
        mark_all_as_read=AsyncMock(return_value=3),
    )
    monkeypatch.setattr(notifications_api, "NotificationService", lambda _db: service)
    current_user = _current_user()
    listed = await notifications_api.list_notifications(current_user, object(), 1, 20, True, "system")
    assert listed.total == 1
    assert (
        await notifications_api.mark_notification_read(notification.id, current_user, object())
    ).id == notification.id
    assert (await notifications_api.mark_all_read(current_user, object())).updated_count == 3

    service.mark_as_read.side_effect = NotFoundError()
    with pytest.raises(HTTPException) as missing:
        await notifications_api.mark_notification_read(notification.id, current_user, object())
    assert missing.value.status_code == 404


@pytest.mark.asyncio
async def test_admin_adapters() -> None:
    current_user = _current_user()
    initial_value = "unit-test-1234"
    replacement_value = "replacement-test-5678"
    assert (await list_audit_events(current_user, object(), 1, 20)).total == 0
    assert (await export_audit_events(current_user, object()))["download_url"]
    assert (await global_search(current_user, object(), "project", 10)).results == []
    assert await settings_api.list_model_providers(current_user, object()) == []
    assert await settings_api.get_model_routes(current_user, object()) == []
    assert (await settings_api.get_generation_settings(current_user, object())).temperature == 0.3
    assert (await settings_api.get_deployment_settings(current_user, object())).mode == "saas"
    assert (await settings_api.get_document_template(current_user, object())).page_size == "A4"
    assert (await settings_api.get_notification_settings(current_user, object())).in_app_enabled
    assert await settings_api.get_agents_status(current_user, object()) == []

    provider = await settings_api.create_model_provider(
        {
            "provider": "deepseek",
            "display_name": "DeepSeek",
            "base_url": "https://api.example.test",
            "api_key": initial_value,
            "enabled": True,
        },
        current_user,
        object(),
    )
    assert provider.api_key_masked.endswith("1234")
    assert (await settings_api.list_model_providers(current_user, object())) == [provider]
    assert (
        await SettingsService(object()).get_decrypted_api_key(  # type: ignore[arg-type]
            provider.id,
            UUID(current_user["tenant_id"]),
        )
        == initial_value
    )

    updated_provider = await settings_api.update_model_provider(
        provider.id,
        {"display_name": "DeepSeek V3", "api_key": replacement_value},
        current_user,
        object(),
    )
    assert updated_provider.display_name == "DeepSeek V3"
    assert updated_provider.key_last_four == "5678"
    assert updated_provider.version == 2
    assert (await settings_api.test_model_provider(provider.id, current_user, object()))["job_id"]

    route = {
        "scene": "evaluation",
        "primary_provider_id": provider.id,
        "primary_model": "deepseek-chat",
        "fallback_provider_id": provider.id,
        "fallback_model": "deepseek-chat",
        "timeout_seconds": 60,
        "max_retries": 3,
        "circuit_breaker_failures": 3,
    }
    assert (await settings_api.update_model_routes({"routes": [route]}, current_user, object()))[
        0
    ].scene == "evaluation"
    assert (
        await settings_api.update_generation_settings({"temperature": 0.7}, current_user, object())
    ).temperature == 0.7
    assert (await settings_api.update_deployment_settings({}, current_user, object())).version == 2
    assert (await settings_api.update_document_template({}, current_user, object())).version == 2
    assert (await settings_api.update_notification_settings({}, current_user, object())).version == 2

    with pytest.raises(NotFoundError):
        await settings_api.update_model_provider(uuid4(), {}, current_user, object())
    with pytest.raises(NotFoundError):
        await settings_api.test_model_provider(uuid4(), current_user, object())
