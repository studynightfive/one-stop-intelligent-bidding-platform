"""M7 测试共享 fixture。"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _ensure_fake_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """默认所有 AI 测试走离线 Provider。"""

    monkeypatch.setenv("AI_FAKE_PROVIDER", "true")
    monkeypatch.setenv("WORKER_EAGER_MODE", "true")
    monkeypatch.setenv("REDIS_URL", "")
    yield


@pytest.fixture
def sample_payload() -> dict[str, object]:
    return {
        "projectName": "智慧校园招投标项目",
        "rawText": (
            "## 项目背景\n"
            "为推动校园数字化建设，现需采购一体化教学管理平台。\n\n"
            "## 技术要求\n"
            "1. 支持国产化操作系统\n"
            "2. 集成 SSO 单点登录\n"
            "3. 提供 API 网关\n"
        ),
    }
