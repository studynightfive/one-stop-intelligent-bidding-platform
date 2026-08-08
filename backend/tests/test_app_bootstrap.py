from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.core.dependencies import get_current_active_user
from app.main import app, create_app
from app.models_registry import Base


def test_contract_is_exposed_by_central_app() -> None:
    response = TestClient(app).get("/api/v1/openapi.json")

    assert response.status_code == 200
    contract = response.json()
    operation_count = sum(
        1
        for path_item in contract["paths"].values()
        for method in path_item
        if method in {"get", "post", "put", "patch", "delete"}
    )
    assert contract["openapi"] == "3.1.0"
    assert operation_count == 158


def test_swagger_ui_is_available() -> None:
    response = TestClient(app).get("/docs")

    assert response.status_code == 200
    assert "Swagger UI" in response.text


def test_contract_path_honors_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    configured = tmp_path / "contract.yaml"
    monkeypatch.setenv("OPENAPI_CONTRACT_PATH", str(configured))

    assert main._contract_path() == configured.resolve()


def test_missing_contract_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAPI_CONTRACT_PATH", str(tmp_path / "missing.yaml"))
    main._load_contract.cache_clear()

    with pytest.raises(RuntimeError, match="OpenAPI contract not found"):
        main._load_contract()

    main._load_contract.cache_clear()


def test_invalid_contract_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    invalid_contract = tmp_path / "invalid.yaml"
    invalid_contract.write_text("openapi: 3.0.0\n", encoding="utf-8")
    monkeypatch.setenv("OPENAPI_CONTRACT_PATH", str(invalid_contract))
    main._load_contract.cache_clear()

    with pytest.raises(RuntimeError, match="valid 3.1.0"):
        main._load_contract()

    main._load_contract.cache_clear()


def test_models_share_the_central_declarative_base() -> None:
    assert Base.metadata is not None
    expected_tables = {
        "audit_events",
        "file_upload_sessions",
        "files",
        "jobs",
        "notifications",
        "users",
        "evaluation_tasks",
        "evaluation_suppliers",
        "supplier_invites",
        "portal_sessions",
        "score_items",
        "evaluation_reports",
    }
    assert expected_tables <= set(Base.metadata.tables)


def test_merged_domain_routes_are_registered() -> None:
    route_paths = {path for route in app.routes if (path := getattr(route, "path", None)) is not None}

    assert {
        "/api/v1/health/live",
        "/api/v1/auth/login",
        "/api/v1/users",
        "/api/v1/files/upload-sessions",
        "/api/v1/jobs/{job_id}",
        "/api/v1/notifications",
        "/api/v1/settings/model-providers",
        "/api/v1/audit-events",
        "/api/v1/global-search",
        "/api/v1/evaluations",
        "/api/v1/portal/session/exchange",
    } <= route_paths


def test_liveness_route_is_available() -> None:
    response = TestClient(app).get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_m6_internal_routes_require_m4_authentication() -> None:
    response = TestClient(create_app(), raise_server_exceptions=False).get("/api/v1/evaluations/stats")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHENTICATED"


def test_m6_internal_routes_accept_m4_user_context() -> None:
    test_app = create_app()

    async def authenticated_leader() -> dict[str, str]:
        return {
            "id": "0190f4dd-0000-7000-8000-000000000001",
            "tenant_id": "0190f4dd-0000-7000-8000-000000000002",
            "role": "admin",
            "name": "Project Leader",
        }

    test_app.dependency_overrides[get_current_active_user] = authenticated_leader
    response = TestClient(test_app).get("/api/v1/evaluations/stats")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["total"] == 0
