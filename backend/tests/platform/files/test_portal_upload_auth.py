"""Supplier portal authentication and least-privilege upload tests."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from app.domains.evaluations.ports import PortalPrincipal
from app.domains.files.api import files as files_api
from app.domains.files.schemas.file import CreateUploadSessionRequest


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/files/upload-sessions",
            "headers": [],
            "app": SimpleNamespace(state=SimpleNamespace()),
        }
    )


@pytest.mark.asyncio
async def test_upload_actor_accepts_a_valid_portal_token(monkeypatch: pytest.MonkeyPatch) -> None:
    unauthorized = HTTPException(status_code=401, detail={"code": "UNAUTHENTICATED"})

    async def reject_internal(*_args: object) -> dict[str, object]:
        raise unauthorized

    monkeypatch.setattr(files_api, "get_current_user", reject_internal)
    supplier_id = str(uuid4())
    tenant_id = str(uuid4())
    portal = SimpleNamespace(
        resolve_principal=lambda token: PortalPrincipal(
            supplier_id=supplier_id,
            evaluation_id=str(uuid4()),
            tenant_id=tenant_id,
            name="受邀供应商",
        )
    )

    actor = await files_api.get_upload_actor(
        _request(),
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="portal-token"),
        object(),  # type: ignore[arg-type]
        SimpleNamespace(portal=portal),  # type: ignore[arg-type]
    )

    assert actor == {
        "id": supplier_id,
        "tenant_id": tenant_id,
        "role": "portal",
        "status": "active",
        "name": "受邀供应商",
        "auth_channel": "portal",
    }


def test_portal_upload_scope_only_allows_bound_supplier_materials() -> None:
    portal_actor = {"auth_channel": "portal"}
    valid = CreateUploadSessionRequest(
        fileName="qualification.pdf",
        mimeType="application/pdf",
        sizeBytes=16,
        sha256="a" * 64,
        purpose="supplierMaterial",
        resourceId=uuid4(),
    )
    files_api._assert_portal_upload_scope(portal_actor, valid)

    invalid_purpose = valid.model_copy(update={"purpose": "tender"})
    with pytest.raises(HTTPException) as purpose_error:
        files_api._assert_portal_upload_scope(portal_actor, invalid_purpose)
    assert purpose_error.value.status_code == 403

    missing_resource = valid.model_copy(update={"resource_id": None})
    with pytest.raises(HTTPException) as resource_error:
        files_api._assert_portal_upload_scope(portal_actor, missing_resource)
    assert resource_error.value.status_code == 422


def test_internal_upload_scope_remains_unchanged() -> None:
    internal_actor = {"role": "admin"}
    request = CreateUploadSessionRequest(
        fileName="tender.pdf",
        mimeType="application/pdf",
        sizeBytes=16,
        sha256="b" * 64,
        purpose="tender",
    )
    files_api._assert_portal_upload_scope(internal_actor, request)
