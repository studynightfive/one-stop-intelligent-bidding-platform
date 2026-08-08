"""公共平台核心设施测试。"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core import database, dependencies
from app.core.config import settings
from app.core.errors import (
    AiProviderUnavailableError,
    AppException,
    AuthenticationError,
    ConflictError,
    DeadlinePassedError,
    FileRejectedError,
    FileTooLargeError,
    ForbiddenError,
    InternalError,
    InvalidCredentialsError,
    InvalidStateTransitionError,
    JobFailedError,
    NotFoundError,
    RateLimitedError,
    TokenExpiredError,
    TokenRevokedError,
    UnsupportedFileTypeError,
    ValidationError,
    VersionConflictError,
    VirusDetectedError,
)
from app.core.errors.handlers import create_error_response, register_exception_handlers
from app.core.redis import RedisClient, add_token_to_blacklist, get_redis, get_token_ttl, is_token_blacklisted
from app.core.security import jwt as security


def test_security_tokens_and_crypto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    private_path = tmp_path / "jwt-private.pem"
    public_path = tmp_path / "jwt-public.pem"
    monkeypatch.setattr(settings, "jwt_private_key_path", private_path)
    monkeypatch.setattr(settings, "jwt_public_key_path", public_path)
    monkeypatch.setattr(settings, "environment", "development")

    private_key, public_key = security._load_or_generate_keys()
    assert private_path.read_bytes() == private_key
    assert public_path.read_bytes() == public_key
    assert security._load_or_generate_keys() == (private_key, public_key)

    access = security.create_access_token("user-1", additional_claims={"role": "admin"})
    assert security.verify_token(access)["role"] == "admin"
    assert security.decode_token_unsafe(access)["sub"] == "user-1"

    refresh = security.create_refresh_token("user-1")
    assert security.verify_token(refresh, "refresh")["jti"]
    with pytest.raises(jwt.InvalidTokenError):
        security.verify_token(refresh)

    portal = security.create_portal_token("invite-1", "supplier-1", "evaluation-1")
    assert security.verify_token(portal, "portal")["supplier_id"] == "supplier-1"

    encrypted = security.encrypt_api_key("sk-secret", b"short-key")
    assert security.decrypt_api_key(encrypted, b"short-key") == "sk-secret"
    monkeypatch.setattr(settings, "model_master_key_path", tmp_path / "missing-master-key")
    encrypted_default = security.encrypt_api_key("default-secret")
    assert security.decrypt_api_key(encrypted_default) == "default-secret"

    assert security.mask_api_key("") == "••••••••"
    assert security.mask_api_key("abc") == "••••abc"
    assert security.mask_api_key("sk-123456") == "••••3456"
    digest = security.compute_sha256(b"payload")
    assert security.verify_sha256(b"payload", digest.upper())
    assert not security.verify_sha256(b"other", digest)
    ticket = security.generate_websocket_ticket()
    assert len(ticket) > 20
    assert security.hash_ticket(ticket) == security.hash_ticket(ticket)


def test_missing_production_keys_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_private_key_path", tmp_path / "missing-private.pem")
    monkeypatch.setattr(settings, "jwt_public_key_path", tmp_path / "missing-public.pem")
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(RuntimeError, match="JWT密钥文件不存在"):
        security._load_or_generate_keys()


def test_password_hash_rejects_invalid_hash() -> None:
    assert security.verify_password("secret", "not-a-bcrypt-hash") is False


def test_exception_catalog_and_error_envelope() -> None:
    errors: list[AppException] = [
        AuthenticationError(),
        TokenExpiredError(),
        InvalidCredentialsError(),
        TokenRevokedError(),
        ForbiddenError(),
        NotFoundError(resource_type="file", resource_id="f-1"),
        ValidationError(field_errors=[{"field": "name", "code": "required", "message": "required"}]),
        ConflictError(),
        VersionConflictError(1, 2),
        DeadlinePassedError(),
        InvalidStateTransitionError("draft", ["publish"], {"resource": "evaluation"}),
        FileRejectedError(),
        FileTooLargeError(1024 * 1024, 2 * 1024 * 1024),
        UnsupportedFileTypeError(".exe", [".pdf"]),
        VirusDetectedError("virus.exe"),
        AiProviderUnavailableError("fake"),
        JobFailedError("job-1", details={"step": "parse"}),
        RateLimitedError(retry_after=30),
        InternalError(),
    ]
    assert all(error.code and error.status_code >= 400 for error in errors)
    assert errors[5].to_dict()["details"]["resourceId"] == "f-1"
    assert errors[6].to_dict()["fieldErrors"][0]["field"] == "name"

    envelope = create_error_response(
        "INVALID",
        "bad request",
        request_id="req-1",
        details={"reason": "test"},
        field_errors=[{"field": "name", "code": "bad", "message": "bad"}],
    )
    assert envelope["requestId"] == "req-1"
    assert envelope["error"]["details"] == {"reason": "test"}


class _Payload(BaseModel):
    count: int


def test_registered_exception_handlers() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/app-error")
    async def app_error() -> None:
        raise NotFoundError(resource_type="item", resource_id="1")

    @app.post("/request-validation")
    async def request_validation(payload: _Payload) -> _Payload:
        return payload

    @app.get("/pydantic-validation")
    async def pydantic_validation() -> None:
        _Payload.model_validate({"count": "invalid"})

    @app.get("/generic")
    async def generic() -> None:
        raise RuntimeError("do not expose")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/app-error", headers={"X-Request-Id": "req-app"})
        assert response.status_code == 404
        assert response.json()["requestId"] == "req-app"

        response = client.post("/request-validation", json={"count": "invalid"})
        assert response.status_code == 422
        assert response.json()["error"]["fieldErrors"]

        response = client.get("/pydantic-validation")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

        response = client.get("/generic")
        assert response.status_code == 500
        assert "do not expose" not in response.text


@pytest.mark.asyncio
async def test_authentication_and_role_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(HTTPException) as missing:
        await dependencies.get_current_user(None)
    assert missing.value.status_code == 401

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    monkeypatch.setattr(dependencies, "decode_token_unsafe", lambda _: {"jti": "jti-1"})
    monkeypatch.setattr(
        "app.core.redis.is_token_blacklisted",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        dependencies,
        "verify_token",
        lambda *_args, **_kwargs: {"sub": "u-1", "tenant_id": "t-1", "role": "admin"},
    )
    current_user = await dependencies.get_current_user(credentials)
    assert current_user["id"] == "u-1"
    assert await dependencies.get_current_active_user(current_user) == current_user
    assert await dependencies.require_admin(current_user) == current_user
    assert await dependencies.require_project_lead_or_admin(current_user) == current_user
    assert await dependencies.require_reviewer_or_admin(current_user) == current_user
    assert await dependencies.require_role("admin")(current_user) == current_user

    for guard in (
        dependencies.require_admin,
        dependencies.require_project_lead_or_admin,
        dependencies.require_reviewer_or_admin,
    ):
        with pytest.raises(HTTPException) as forbidden:
            await guard({"role": "member"})
        assert forbidden.value.status_code == 403
    with pytest.raises(HTTPException):
        await dependencies.require_role("admin")({"role": "member"})

    monkeypatch.setattr(dependencies, "verify_token", lambda *_args, **_kwargs: {"role": "member"})
    with pytest.raises(HTTPException) as invalid:
        await dependencies.get_current_user(credentials)
    assert invalid.value.status_code == 401


@pytest.mark.asyncio
async def test_portal_and_database_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(HTTPException):
        await dependencies.get_portal_user(None)

    monkeypatch.setattr(
        dependencies,
        "verify_token",
        lambda *_args, **_kwargs: {"sub": "invite", "supplier_id": "supplier", "evaluation_id": "evaluation"},
    )
    portal = await dependencies.get_portal_user("portal-token")
    assert portal["supplier_id"] == "supplier"

    monkeypatch.setattr(dependencies, "verify_token", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError()))
    with pytest.raises(HTTPException):
        await dependencies.get_portal_user("bad-token")

    session = object()

    async def fake_get_db() -> AsyncGenerator[Any, None]:
        yield session

    monkeypatch.setattr(dependencies, "get_db", fake_get_db)
    yielded = [item async for item in dependencies.get_db_session()]
    assert yielded == [session]

    monkeypatch.setattr(
        settings,
        "database_url",
        "postgresql+asyncpg://user@localhost:5432/platform",
    )
    engine = database._create_async_engine()
    assert type(engine.pool).__name__ == "AsyncAdaptedQueuePool"
    await engine.dispose()


@pytest.mark.asyncio
async def test_redis_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = SimpleNamespace(
        setex=AsyncMock(),
        exists=AsyncMock(return_value=1),
        ttl=AsyncMock(return_value=29),
        close=AsyncMock(),
    )
    client = RedisClient()
    monkeypatch.setattr(client, "_client", fake)

    assert await get_redis() is fake
    await add_token_to_blacklist("jti", 30)
    assert fake.setex.await_args.args[1] == 90
    assert await is_token_blacklisted("jti") is True
    assert await get_token_ttl("jti") == 29
    await client.close()
    assert client._client is None
