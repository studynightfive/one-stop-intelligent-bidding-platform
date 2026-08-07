"""M6 领域错误；映射到契约 ErrorCode，不替代 M4 全局异常中间件。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DomainError(Exception):
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    field_errors: list[dict[str, str]] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def not_found(message: str = "资源不存在", **details: Any) -> DomainError:
    return DomainError(code="NOT_FOUND", message=message, details=details)


def forbidden(message: str = "无权访问", **details: Any) -> DomainError:
    return DomainError(code="FORBIDDEN", message=message, details=details)


def conflict(message: str, **details: Any) -> DomainError:
    return DomainError(code="CONFLICT", message=message, details=details)


def version_conflict(current_version: int) -> DomainError:
    return DomainError(
        code="VERSION_CONFLICT",
        message="资源版本冲突，请刷新后重试",
        details={"currentVersion": current_version},
    )


def invalid_transition(current_status: str, allowed_actions: list[str]) -> DomainError:
    return DomainError(
        code="INVALID_STATE_TRANSITION",
        message="当前状态不允许该操作",
        details={"currentStatus": current_status, "allowedActions": allowed_actions},
    )


def deadline_passed(message: str = "已过截止时间", **details: Any) -> DomainError:
    return DomainError(code="DEADLINE_PASSED", message=message, details=details)


def validation_error(message: str, field_errors: list[dict[str, str]] | None = None) -> DomainError:
    return DomainError(
        code="VALIDATION_ERROR",
        message=message,
        field_errors=field_errors or [],
    )
