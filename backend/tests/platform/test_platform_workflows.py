"""End-to-end unit coverage for M4 platform workflows and contract adapters."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from email.message import EmailMessage
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core import dependencies
from app.core.errors import AuthenticationError
from app.domains.audit.mappers import audit_event_to_data
from app.domains.audit.services.audit_service import AuditService
from app.domains.auth.api import auth as auth_api
from app.domains.auth.api import users as users_api
from app.domains.auth.models.user import UserRole, UserStatus
from app.domains.auth.schemas.auth import (
    ForgotPasswordRequest,
    InviteUserRequest,
    LoginRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UpdateUserRequest,
    UserStatusRequest,
)
from app.domains.auth.services.auth_service import AuthService
from app.domains.auth.services.email_service import EmailService
from app.domains.search import api as search_api


def _request(
    method: str,
    path: str,
    *,
    state: SimpleNamespace | None = None,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": headers or [(b"x-request-id", b"workflow-request")],
            "app": SimpleNamespace(state=state or SimpleNamespace()),
        }
    )


def _body(response: Response) -> dict[str, object]:
    return json.loads(response.body)


@pytest.mark.asyncio
async def test_auth_http_and_password_reset_workflow(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AuthService(db_session)
    tenant_id = uuid4()
    user = await service.register(
        email="workflow@example.com",
        password="InitialPassword123",
        name="Workflow User",
        tenant_id=tenant_id,
        role=UserRole.ADMIN,
    )
    current_user = {
        "id": str(user.id),
        "tenant_id": str(tenant_id),
        "role": "admin",
        "status": "active",
        "jti": "logout-jti",
    }

    logged_in = await auth_api.login(
        LoginRequest(email=user.email, password="InitialPassword123"),
        _request("POST", "/api/v1/auth/login"),
        db_session,
    )
    assert _body(logged_in)["data"]["user"]["id"] == str(user.id)  # type: ignore[index]

    me = await auth_api.get_current_user_info(_request("GET", "/api/v1/auth/me"), current_user, db_session)
    assert _body(me)["data"]["email"] == user.email  # type: ignore[index]
    updated = await auth_api.update_profile(
        UpdateProfileRequest(name="Updated Workflow", department="PMO"),
        _request("PATCH", "/api/v1/auth/me"),
        current_user,
        db_session,
    )
    assert _body(updated)["data"]["name"] == "Updated Workflow"  # type: ignore[index]

    mailer = SimpleNamespace(send_password_reset=AsyncMock(return_value=True))
    monkeypatch.setattr(auth_api, "EmailService", lambda: mailer)
    forgot = await auth_api.forgot_password(
        ForgotPasswordRequest(email=user.email),
        _request("POST", "/api/v1/auth/password/forgot"),
        db_session,
    )
    assert _body(forgot)["data"] == {"accepted": True}
    mailer.send_password_reset.assert_awaited_once()

    refreshed_user = await service.get_user_by_id(user.id)
    assert refreshed_user is not None
    reset_token = service.create_password_reset_token(refreshed_user)
    reset = await auth_api.reset_password(
        ResetPasswordRequest(resetToken=reset_token, newPassword="ReplacementPassword456"),
        _request("POST", "/api/v1/auth/password/reset"),
        db_session,
    )
    assert _body(reset)["data"] == {"reset": True}
    assert (await service.authenticate(user.email, "ReplacementPassword456")).id == user.id

    with pytest.raises(AuthenticationError):
        await service.reset_password(reset_token, "AnotherPassword789")
    with pytest.raises(HTTPException) as invalid_reset:
        await auth_api.reset_password(
            ResetPasswordRequest(resetToken="invalid-token", newPassword="AnotherPassword789"),
            _request("POST", "/api/v1/auth/password/reset"),
            db_session,
        )
    assert invalid_reset.value.status_code == 400

    tokens = await service.create_tokens(refreshed_user)
    refresh_request = _request(
        "POST",
        "/api/v1/auth/refresh",
        headers=[(b"cookie", f"refresh_token={tokens['refresh_token']}".encode())],
    )
    refreshed = await auth_api.refresh_token(refresh_request, db_session)
    assert _body(refreshed)["data"]["accessToken"]  # type: ignore[index]

    blacklist = AsyncMock()
    monkeypatch.setattr("app.core.redis.add_token_to_blacklist", blacklist)
    logged_out = await auth_api.logout(_request("POST", "/api/v1/auth/logout"), current_user)
    assert _body(logged_out)["data"] == {"loggedOut": True}
    blacklist.assert_awaited_once()

    monkeypatch.setattr("app.core.redis.is_token_blacklisted", AsyncMock(return_value=False))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=tokens["access_token"])
    verified = await dependencies.get_current_user(credentials, db_session)
    assert verified["name"] == "Updated Workflow"

    refreshed_user.status = UserStatus.DISABLED
    await db_session.commit()
    with pytest.raises(HTTPException) as disabled:
        await dependencies.get_current_user(credentials, db_session)
    assert disabled.value.detail["code"] == "ACCOUNT_DISABLED"


@pytest.mark.asyncio
async def test_user_management_project_activity_and_metadata_workflow(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_service = AuthService(db_session)
    tenant_id = uuid4()
    admin = await auth_service.register(
        email="admin-workflow@example.com",
        password="AdminPassword123",
        name="Admin",
        tenant_id=tenant_id,
        role=UserRole.ADMIN,
    )
    current_user = {
        "id": str(admin.id),
        "tenant_id": str(tenant_id),
        "role": "admin",
        "name": admin.name,
    }
    mailer = SimpleNamespace(
        send_invitation=AsyncMock(return_value=True),
        send_password_reset=AsyncMock(return_value=True),
    )
    monkeypatch.setattr(users_api, "EmailService", lambda: mailer)

    invited_response = await users_api.invite_user(
        InviteUserRequest(
            email="member-workflow@example.com",
            name="Member",
            role="member",
            department="技术部",
        ),
        _request("POST", "/api/v1/users/invitations"),
        current_user,
        db_session,
    )
    invited_data = _body(invited_response)["data"]  # type: ignore[assignment]
    invited_id = UUID(invited_data["user"]["id"])
    assert invited_data["invitationExpiresAt"]

    listed = await users_api.list_users(
        _request("GET", "/api/v1/users"),
        current_user,
        db_session,
        1,
        20,
        "name",
        "asc",
        "Member",
        "member",
        "技术部",
        "invited",
    )
    assert _body(listed)["meta"]["total"] == 1  # type: ignore[index]

    resent = await users_api.resend_invitation(
        invited_id,
        _request("POST", f"/api/v1/users/{invited_id}/invitations/resend"),
        current_user,
        db_session,
    )
    assert _body(resent)["data"] == {"sent": True}

    updated = await users_api.update_user(
        invited_id,
        UpdateUserRequest(name="Member Updated", role="reviewer"),
        _request("PATCH", f"/api/v1/users/{invited_id}"),
        current_user,
        db_session,
        '"1"',
    )
    assert _body(updated)["data"]["role"] == "reviewer"  # type: ignore[index]

    reset_email = await users_api.send_password_reset_email(
        invited_id,
        _request("POST", f"/api/v1/users/{invited_id}/password-reset-email"),
        current_user,
        db_session,
    )
    assert _body(reset_email)["data"] == {"sent": True}

    now = datetime.now(UTC)
    bid = SimpleNamespace(
        id=str(uuid4()),
        project_name="投标项目",
        tender_no="BID-001",
        status="draft",
        assignee_id=str(invited_id),
        assignments=[],
        updated_at=now,
        created_at=now,
    )
    evaluation = SimpleNamespace(
        id=str(uuid4()),
        project_name="评标项目",
        tender_no="EVAL-001",
        status="pending",
        assignee_id=str(admin.id),
        reviewer_ids=[str(invited_id)],
        updated_at=now,
    )
    state = SimpleNamespace(
        m5_bid_store=SimpleNamespace(list_tasks=lambda **_kwargs: [bid]),
        m6_store=SimpleNamespace(list_evaluations=lambda **_kwargs: [evaluation]),
    )
    projects = await users_api.get_user_projects(
        invited_id,
        _request("GET", f"/api/v1/users/{invited_id}/projects", state=state),
        current_user,
        db_session,
        1,
        20,
        "updatedAt",
        "desc",
    )
    assert _body(projects)["meta"]["total"] == 2  # type: ignore[index]

    event = await AuditService(db_session).log_user_action(
        tenant_id=tenant_id,
        user_id=invited_id,
        user_name="Member Updated",
        aggregate_type="user",
        aggregate_id=invited_id,
        action="update",
        summary="更新个人资料",
        changes={"name": {"old": "Member", "new": "Member Updated"}},
        request_id="activity-request",
        target_type="user",
        target_id=invited_id,
        ip_address="127.0.0.1",
    )
    mapped = audit_event_to_data(event)
    assert mapped["changes"] == [{"field": "name", "oldValue": "Member", "newValue": "Member Updated"}]

    activity = await users_api.get_user_activity(
        invited_id,
        _request("GET", f"/api/v1/users/{invited_id}/activity"),
        current_user,
        db_session,
        1,
        20,
        "createdAt",
        "asc",
        None,
        None,
    )
    assert _body(activity)["meta"]["total"] == 1  # type: ignore[index]

    roles = await users_api.list_roles(_request("GET", "/api/v1/roles"), current_user, db_session)
    assert sum(item["userCount"] for item in _body(roles)["data"]) == 2  # type: ignore[index]
    matrix = await users_api.get_permissions_matrix(_request("GET", "/api/v1/permissions/matrix"), current_user)
    assert _body(matrix)["data"]["modules"][0]["actions"]["write"] == ["admin"]  # type: ignore[index]

    status_response = await users_api.set_user_status(
        invited_id,
        UserStatusRequest(status="disabled", reason="成员离职"),
        _request("POST", f"/api/v1/users/{invited_id}/status"),
        current_user,
        db_session,
    )
    assert _body(status_response)["data"]["status"] == "disabled"  # type: ignore[index]

    with pytest.raises(HTTPException) as forbidden:
        users_api._ensure_self_or_admin(invited_id, {**current_user, "role": "member"})
    assert forbidden.value.status_code == 403


@pytest.mark.asyncio
async def test_email_delivery_success_failure_and_smtp_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[EmailMessage] = []

    class FakeSmtp:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            assert host and port and timeout == 10

        def __enter__(self) -> FakeSmtp:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def starttls(self) -> None:
            return None

        def login(self, username: str, password: str) -> None:
            assert username == "smtp-user" and password == "smtp-password"

        def send_message(self, message: EmailMessage) -> None:
            sent.append(message)

    from app.domains.auth.services import email_service

    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSmtp)
    monkeypatch.setattr(email_service.settings, "mail_use_tls", True)
    monkeypatch.setattr(email_service.settings, "mail_username", "smtp-user")
    monkeypatch.setattr(email_service.settings, "mail_password", "smtp-password")
    service = EmailService()
    assert await service.send_invitation(email="member@example.com", name="Member", token="invite-token")
    assert await service.send_password_reset(email="member@example.com", name="Member", token="reset-token")
    assert len(sent) == 2

    def fail_delivery(_message: EmailMessage) -> None:
        raise OSError("smtp unavailable")

    monkeypatch.setattr(service, "_send_sync", fail_delivery)
    assert not await service.send_password_reset(email="member@example.com", name="Member", token="reset-token")


@pytest.mark.asyncio
async def test_global_search_uses_every_live_store() -> None:
    now = datetime.now(UTC)
    user_id = str(uuid4())
    tenant_id = str(uuid4())
    bid = SimpleNamespace(
        id=str(uuid4()),
        project_name="投标项目",
        tender_no="BID-001",
        tender_entity="采购人",
        assignee_id=user_id,
        assignments=[],
    )
    evaluation = SimpleNamespace(
        id=str(uuid4()),
        project_name="投标项目评审",
        tender_no="EVAL-001",
        tender_entity="采购人",
        assignee_id=user_id,
        reviewer_ids=[],
        updated_at=now,
    )
    qualification = SimpleNamespace(id=str(uuid4()), name="投标资质", category="企业证照", cert_number="CERT-1")
    fragment = SimpleNamespace(id=str(uuid4()), title="投标技术片段", category="技术", summary="项目方案")
    state = SimpleNamespace(
        m5_bid_store=SimpleNamespace(list_tasks=lambda **_kwargs: [bid]),
        m6_store=SimpleNamespace(list_evaluations=lambda **_kwargs: [evaluation]),
        m5_qualification_store=SimpleNamespace(list=lambda **_kwargs: [qualification]),
        m5_fragment_store=SimpleNamespace(list_active=lambda **_kwargs: [fragment]),
    )
    response = await search_api.global_search(
        _request("GET", "/api/v1/global-search", state=state),
        {"id": user_id, "tenant_id": tenant_id, "role": "admin"},
        object(),  # type: ignore[arg-type]
        "投标",
        20,
    )
    result_types = {item["type"] for item in _body(response)["data"]}  # type: ignore[union-attr]
    assert {"page", "bidTask", "evaluation", "qualification", "fragment"} <= result_types
    assert search_api._score("完全一致", "完全一致") == 1.0
    assert search_api._score("完全", "完全一致") == 0.92
    assert search_api._score("一致", "完全一致") == 0.82
    assert search_api._score("副标题", "无", "包含副标题") == 0.62
    assert search_api._score("未命中", "无", "无") == 0.0
