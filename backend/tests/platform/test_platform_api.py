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
from app.domains.audit import api as audit_api
from app.domains.auth.api import auth as auth_api
from app.domains.auth.schemas.auth import LoginRequest
from app.domains.files.api import files as files_api
from app.domains.files.schemas.file import CompleteUploadRequest, CreateUploadSessionRequest
from app.domains.jobs.api import jobs as jobs_api
from app.domains.jobs.models.job import JobStatus, JobType
from app.domains.notifications import api as notifications_api
from app.domains.notifications.models.notification import NotificationType
from app.domains.search import api as search_api
from app.domains.settings import api as settings_api
from app.domains.settings.schemas.settings import (
    DeploymentSettingsRequest,
    DocumentTemplateRequest,
    GenerationSettingsRequest,
    ModelProviderRequest,
    NotificationSettingsRequest,
    UpdateModelProviderRequest,
)
from app.domains.settings.services.settings_service import SettingsService


def _current_user() -> dict[str, str]:
    return {"id": str(uuid4()), "tenant_id": str(uuid4()), "role": "admin"}


def _request(method: str, path: str, request_id: str = "file-request") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [(b"x-request-id", request_id.encode())],
            "app": SimpleNamespace(state=SimpleNamespace()),
        }
    )


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
        sha256="a" * 64,
        scan_status=SimpleNamespace(value="clean"),
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_file_api_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    file_record = _file()
    service = SimpleNamespace(
        create_upload_session=AsyncMock(return_value=session),
        get_upload_session=AsyncMock(return_value=session),
        upload_part=AsyncMock(return_value=(session, "etag")),
        complete_upload=AsyncMock(return_value=file_record),
        cancel_upload_session=AsyncMock(),
        open_file=AsyncMock(return_value=(file_record, object())),
    )
    monkeypatch.setattr(files_api, "FileService", lambda _db: service)
    current_user = _current_user()
    body = CreateUploadSessionRequest(
        fileName="proposal.pdf",
        mimeType="application/pdf",
        sizeBytes=10,
        sha256="a" * 64,
        purpose="tender",
    )

    created_response = await files_api.create_upload_session(
        body,
        _request("POST", "/api/v1/files/upload-sessions"),
        current_user,
        object(),  # type: ignore[arg-type]
    )
    created = json.loads(created_response.body)
    upload_id = UUID(created["data"]["id"])
    assert created["success"] is True
    assert created["data"]["fileName"] == "proposal.pdf"
    assert "file_name" not in created["data"]

    queried_response = await files_api.get_upload_session(
        upload_id,
        _request("GET", f"/api/v1/files/upload-sessions/{upload_id}"),
        current_user,
        object(),  # type: ignore[arg-type]
    )
    assert json.loads(queried_response.body)["data"]["id"] == str(upload_id)

    uploaded_response = await files_api.upload_part(
        upload_id,
        1,
        b"0123456789",
        _request("PUT", f"/api/v1/files/upload-sessions/{upload_id}/parts/1"),
        current_user,
        object(),  # type: ignore[arg-type]
    )
    assert json.loads(uploaded_response.body)["data"] == {"partNumber": 1, "etag": "etag"}

    completed_response = await files_api.complete_upload(
        upload_id,
        CompleteUploadRequest(parts=[{"partNumber": 1, "etag": "etag"}]),
        _request("POST", f"/api/v1/files/upload-sessions/{upload_id}/complete"),
        current_user,
        object(),  # type: ignore[arg-type]
        "idempotency-file-upload",
    )
    completed = json.loads(completed_response.body)
    file_id = UUID(completed["data"]["id"])
    assert completed["data"]["fileName"] == "proposal.pdf"

    cancelled = await files_api.cancel_upload(
        upload_id,
        _request("DELETE", f"/api/v1/files/upload-sessions/{upload_id}"),
        current_user,
        object(),  # type: ignore[arg-type]
    )
    assert cancelled.status_code == 204

    preview = await files_api.preview_file(
        file_id,
        _request("GET", f"/api/v1/files/{file_id}/preview"),
        current_user,
        object(),  # type: ignore[arg-type]
    )
    download = await files_api.download_file(
        file_id,
        _request("GET", f"/api/v1/files/{file_id}/download"),
        current_user,
        object(),  # type: ignore[arg-type]
    )
    assert preview.headers["content-disposition"].startswith("inline")
    assert download.headers["content-disposition"].startswith("attachment")


@pytest.mark.asyncio
async def test_file_api_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    service = SimpleNamespace(
        get_upload_session=AsyncMock(return_value=None),
        complete_upload=AsyncMock(side_effect=FileRejectedError()),
        open_file=AsyncMock(side_effect=NotFoundError()),
    )
    monkeypatch.setattr(files_api, "FileService", lambda _db: service)
    current_user = _current_user()
    identifier = uuid4()
    with pytest.raises(NotFoundError):
        await files_api.get_upload_session(
            identifier,
            _request("GET", f"/api/v1/files/upload-sessions/{identifier}"),
            current_user,
            object(),  # type: ignore[arg-type]
        )
    with pytest.raises(FileRejectedError):
        await files_api.complete_upload(
            identifier,
            CompleteUploadRequest(parts=[{"partNumber": 1, "etag": "etag"}]),
            _request("POST", f"/api/v1/files/upload-sessions/{identifier}/complete"),
            current_user,
            object(),  # type: ignore[arg-type]
            "idempotency-file-upload",
        )
    with pytest.raises(NotFoundError):
        await files_api.preview_file(
            identifier,
            _request("GET", f"/api/v1/files/{identifier}/preview"),
            current_user,
            object(),  # type: ignore[arg-type]
        )
    with pytest.raises(NotFoundError):
        await files_api.download_file(
            identifier,
            _request("GET", f"/api/v1/files/{identifier}/download"),
            current_user,
            object(),  # type: ignore[arg-type]
        )


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
    cancelled_job = _job()
    cancelled_job.status = JobStatus.CANCELLED
    service = SimpleNamespace(
        get_job_for_user=AsyncMock(return_value=job),
        cancel_job=AsyncMock(return_value=cancelled_job),
    )
    monkeypatch.setattr(jobs_api, "JobService", lambda _db: service)
    current_user = _current_user()
    response = await jobs_api.get_job(job.id, _request("GET", f"/api/v1/jobs/{job.id}"), current_user, object())
    assert json.loads(response.body)["data"]["progressPercent"] == 50
    response = await jobs_api.cancel_job(
        job.id,
        _request("POST", f"/api/v1/jobs/{job.id}/cancel"),
        current_user,
        object(),
    )
    assert json.loads(response.body)["data"]["status"] == "cancelled"

    for error, expected in ((NotFoundError(), 404), (ForbiddenError(), 403)):
        service.get_job_for_user.side_effect = error
        with pytest.raises(HTTPException) as raised:
            await jobs_api.get_job(job.id, _request("GET", f"/api/v1/jobs/{job.id}"), current_user, object())
        assert raised.value.status_code == expected

    for error, expected in ((NotFoundError(), 404), (ForbiddenError(), 403), (ValidationError(), 400)):
        service.get_job_for_user.side_effect = None
        service.get_job_for_user.return_value = job
        service.cancel_job.side_effect = error
        with pytest.raises(HTTPException) as raised:
            await jobs_api.cancel_job(
                job.id,
                _request("POST", f"/api/v1/jobs/{job.id}/cancel"),
                current_user,
                object(),
            )
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
    listed = await notifications_api.list_notifications(
        _request("GET", "/api/v1/notifications"), current_user, object(), 1, 20, True, "system", "createdAt", "desc"
    )
    assert json.loads(listed.body)["meta"]["total"] == 1
    marked = await notifications_api.mark_notification_read(
        notification.id,
        {"isRead": True},
        _request("PATCH", f"/api/v1/notifications/{notification.id}"),
        current_user,
        object(),
        '"1"',
    )
    assert json.loads(marked.body)["data"]["id"] == str(notification.id)
    marked_all = await notifications_api.mark_all_read(
        _request("POST", "/api/v1/notifications/read-all"), current_user, object(), "idempotency-test"
    )
    assert json.loads(marked_all.body)["data"]["updatedCount"] == 3

    service.mark_as_read.side_effect = NotFoundError()
    with pytest.raises(HTTPException) as missing:
        await notifications_api.mark_notification_read(
            notification.id,
            {"isRead": True},
            _request("PATCH", f"/api/v1/notifications/{notification.id}"),
            current_user,
            object(),
            '"1"',
        )
    assert missing.value.status_code == 404


@pytest.mark.asyncio
async def test_admin_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    current_user = _current_user()
    initial_value = "unit-test-1234"
    replacement_value = "replacement-test-5678"
    audit_service = SimpleNamespace(list_events=AsyncMock(return_value=([], 0)))
    monkeypatch.setattr(audit_api, "AuditService", lambda _db: audit_service)
    listed = await audit_api.list_audit_events(
        _request("GET", "/api/v1/audit-events"),
        current_user,
        object(),
        1,
        20,
        "createdAt",
        "desc",
        None,
        None,
        None,
        None,
        None,
    )
    assert json.loads(listed.body)["meta"]["total"] == 0
    exported = await audit_api.export_audit_events(
        _request("GET", "/api/v1/audit-events/export"), current_user, object(), None, None, None, None, None
    )
    assert exported.media_type.endswith("spreadsheetml.sheet")
    searched = await search_api.global_search(
        _request("GET", "/api/v1/global-search"), current_user, object(), "project", 10
    )
    assert json.loads(searched.body)["data"] == []
    assert (
        json.loads((await settings_api.list_model_providers(_request("GET", "/"), current_user, object())).body)["data"]
        == []
    )
    assert (
        json.loads((await settings_api.get_model_routes(_request("GET", "/"), current_user, object())).body)["data"]
        == []
    )
    generation = await settings_api.get_generation_settings(_request("GET", "/"), current_user, object())
    assert json.loads(generation.body)["data"]["temperature"] == 0.3
    deployment = await settings_api.get_deployment_settings(_request("GET", "/"), current_user, object())
    assert json.loads(deployment.body)["data"]["mode"] == "saas"
    document = await settings_api.get_document_template(_request("GET", "/"), current_user, object())
    assert json.loads(document.body)["data"]["pageSize"] == "A4"
    notification_settings = await settings_api.get_notification_settings(_request("GET", "/"), current_user, object())
    assert json.loads(notification_settings.body)["data"]["inAppEnabled"] is True
    monkeypatch.setattr(settings_api, "_worker_snapshot", lambda: ("online", 0))
    agents = await settings_api.get_agents_status(_request("GET", "/"), current_user, object())
    assert len(json.loads(agents.body)["data"]) == 5

    provider_response = await settings_api.create_model_provider(
        ModelProviderRequest(
            provider="deepseek",
            displayName="DeepSeek",
            baseUrl="https://api.example.test",
            apiKey=initial_value,
            enabled=True,
        ),
        _request("POST", "/"),
        current_user,
        object(),
    )
    provider = json.loads(provider_response.body)["data"]
    assert provider["apiKeyMasked"].endswith("1234")
    providers = await settings_api.list_model_providers(_request("GET", "/"), current_user, object())
    assert json.loads(providers.body)["data"] == [provider]
    assert (
        await SettingsService(object()).get_decrypted_api_key(  # type: ignore[arg-type]
            UUID(provider["id"]),
            UUID(current_user["tenant_id"]),
        )
        == initial_value
    )

    updated_response = await settings_api.update_model_provider(
        UUID(provider["id"]),
        UpdateModelProviderRequest(displayName="DeepSeek V3", apiKey=replacement_value),
        _request("PATCH", "/"),
        current_user,
        object(),
        '"1"',
    )
    updated_provider = json.loads(updated_response.body)["data"]
    assert updated_provider["displayName"] == "DeepSeek V3"
    assert updated_provider["keyLastFour"] == "5678"
    assert updated_provider["version"] == 2

    job = _job()
    job_service = SimpleNamespace(
        create_job=AsyncMock(return_value=job),
        mark_job_started=AsyncMock(return_value=job),
        mark_job_succeeded=AsyncMock(return_value=job),
        mark_job_failed=AsyncMock(return_value=job),
    )
    monkeypatch.setattr(settings_api, "JobService", lambda _db: job_service)
    tested = await settings_api.test_model_provider(UUID(provider["id"]), _request("POST", "/"), current_user, object())
    assert json.loads(tested.body)["data"]["id"] == str(job.id)

    route = {
        "scene": "evaluation_score",
        "primaryProviderId": provider["id"],
        "primaryModel": "deepseek-chat",
        "fallbackProviderId": provider["id"],
        "fallbackModel": "deepseek-chat",
        "timeoutSeconds": 60,
        "maxRetries": 3,
        "circuitBreakerFailures": 3,
    }
    routes = await settings_api.update_model_routes({"routes": [route]}, _request("PUT", "/"), current_user, object())
    assert json.loads(routes.body)["data"][0]["scene"] == "evaluation_score"
    generation = await settings_api.update_generation_settings(
        GenerationSettingsRequest(temperature=0.7), _request("PUT", "/"), current_user, object()
    )
    assert json.loads(generation.body)["data"]["temperature"] == 0.7
    deployment = await settings_api.update_deployment_settings(
        DeploymentSettingsRequest(
            mode="saas",
            companyName="示例公司",
            storageQuotaBytes=500,
            maxProjects=50,
            maxUsers=30,
            autoBackup=True,
            backupCron="0 2 * * *",
            versionControlEnabled=True,
        ),
        _request("PUT", "/"),
        current_user,
        object(),
    )
    assert json.loads(deployment.body)["data"]["version"] == 2
    document = await settings_api.update_document_template(
        DocumentTemplateRequest(), _request("PUT", "/"), current_user, object()
    )
    assert json.loads(document.body)["data"]["version"] == 2
    notification_settings = await settings_api.update_notification_settings(
        NotificationSettingsRequest(events={}), _request("PUT", "/"), current_user, object()
    )
    assert json.loads(notification_settings.body)["data"]["version"] == 2

    with pytest.raises(NotFoundError):
        await settings_api.update_model_provider(
            uuid4(), UpdateModelProviderRequest(), _request("PATCH", "/"), current_user, object(), '"1"'
        )
    with pytest.raises(NotFoundError):
        await settings_api.test_model_provider(uuid4(), _request("POST", "/"), current_user, object())
