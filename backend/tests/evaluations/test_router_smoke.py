"""M6 HTTP 路由冒烟（不修改中央 Router，本地挂载领域 router）。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domains.evaluations.container import build_m6_container
from app.domains.evaluations.errors import DomainError
from app.domains.evaluations.ports import AuthPrincipal
from app.domains.evaluations.router import auth_principal_from_context, get_actor
from app.domains.evaluations.router import router as evaluations_router
from app.domains.portal.router import router as portal_router


def _app() -> tuple[FastAPI, object]:
    app = FastAPI()
    container = build_m6_container()
    app.state.m6 = container
    app.include_router(evaluations_router, prefix="/api/v1")
    app.include_router(portal_router, prefix="/api/v1")
    app.dependency_overrides[get_actor] = lambda: AuthPrincipal(
        user_id="u-owner",
        tenant_id="t-1",
        name="Owner",
        role="admin",
    )
    return app, container


def test_create_evaluation_http() -> None:
    app, _ = _app()
    client = TestClient(app)
    now = datetime.now(UTC)
    headers = {
        "X-Debug-User-Id": "u-owner",
        "X-Debug-Tenant-Id": "t-1",
        "X-Debug-Role": "admin",
        "X-Debug-User-Name": "Owner",
    }
    response = client.post(
        "/api/v1/evaluations",
        headers=headers,
        json={
            "projectName": "HTTP 评标",
            "tenderNo": "ZB-H-1",
            "tenderEntity": "业主",
            "budgetAmount": "100.00",
            "currency": "CNY",
            "assigneeId": "u-owner",
            "supplierDeadline": (now + timedelta(days=2)).isoformat().replace("+00:00", "Z"),
            "evaluationStartAt": (now + timedelta(days=3)).isoformat().replace("+00:00", "Z"),
            "evaluationEndAt": (now + timedelta(days=9)).isoformat().replace("+00:00", "Z"),
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["projectName"] == "HTTP 评标"
    assert "requestId" in body


def test_auth_context_mapping_and_missing_integration() -> None:
    principal = auth_principal_from_context(
        {
            "id": "u-1",
            "tenant_id": "t-1",
            "name": "评委",
            "role": "reviewer",
            "permissions": ["evaluation:read"],
        }
    )
    assert principal.role == "reviewer"
    assert principal.permissions == ("evaluation:read",)
    assert auth_principal_from_context({"id": "u-2", "tenant_id": "t-1", "role": "unknown"}).role == "member"
    with pytest.raises(DomainError):
        auth_principal_from_context({"id": "u-3"})

    app = FastAPI()
    app.state.m6 = build_m6_container()
    app.include_router(evaluations_router, prefix="/api/v1")
    response = TestClient(app).get("/api/v1/evaluations/stats")
    assert response.status_code == 401
