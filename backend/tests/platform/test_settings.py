from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config.settings import Settings


def test_cors_origins_accept_documented_comma_separated_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://127.0.0.1:3210, https://demo.example.com")

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://127.0.0.1:3210", "https://demo.example.com"]


def test_cors_origins_remain_compatible_with_json_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://localhost:3000"]


def test_cors_origins_reject_invalid_json_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "[invalid")

    with pytest.raises(ValidationError, match="comma-separated list or JSON array"):
        Settings(_env_file=None)
