"""公共平台模块的启动烟测。

这些断言确保领域模块可以在统一运行环境中导入，并且 HTTP Router、服务端口
与模型不会因循环依赖或缺失依赖而阻止应用启动。
"""

from __future__ import annotations

import importlib

import pytest
from fastapi import APIRouter

PLATFORM_MODULES = (
    "app.core.config",
    "app.core.database",
    "app.core.dependencies",
    "app.core.errors",
    "app.core.errors.handlers",
    "app.core.logging",
    "app.core.redis",
    "app.core.security",
    "app.domains.audit.api",
    "app.domains.audit.models",
    "app.domains.audit.schemas",
    "app.domains.audit.services",
    "app.domains.auth.api",
    "app.domains.auth.api.auth",
    "app.domains.auth.api.users",
    "app.domains.auth.models",
    "app.domains.auth.schemas",
    "app.domains.auth.services",
    "app.domains.files.api",
    "app.domains.files.api.files",
    "app.domains.files.models",
    "app.domains.files.models.file",
    "app.domains.files.schemas",
    "app.domains.files.schemas.file",
    "app.domains.files.services",
    "app.domains.files.services.file_service",
    "app.domains.health",
    "app.domains.jobs.api",
    "app.domains.jobs.models",
    "app.domains.jobs.schemas",
    "app.domains.jobs.services",
    "app.domains.notifications.api",
    "app.domains.notifications.models",
    "app.domains.notifications.schemas",
    "app.domains.notifications.services",
    "app.domains.search.api",
    "app.domains.search.schemas",
    "app.domains.settings.api",
    "app.domains.settings.schemas",
    "app.domains.settings.services",
)


@pytest.mark.parametrize("module_name", PLATFORM_MODULES)
def test_platform_module_imports(module_name: str) -> None:
    assert importlib.import_module(module_name).__name__ == module_name


@pytest.mark.parametrize(
    ("module_name", "attribute"),
    (
        ("app.domains.audit.api", "router"),
        ("app.domains.auth.api", "auth_router"),
        ("app.domains.auth.api", "users_router"),
        ("app.domains.files.api", "files_router"),
        ("app.domains.health", "router"),
        ("app.domains.jobs.api", "jobs_router"),
        ("app.domains.notifications.api", "router"),
        ("app.domains.search.api", "router"),
        ("app.domains.settings.api", "router"),
    ),
)
def test_platform_router_is_exported(module_name: str, attribute: str) -> None:
    module = importlib.import_module(module_name)
    router = getattr(module, attribute)
    assert isinstance(router, APIRouter)
    assert router.routes
