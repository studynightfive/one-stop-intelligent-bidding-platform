from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import app
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
