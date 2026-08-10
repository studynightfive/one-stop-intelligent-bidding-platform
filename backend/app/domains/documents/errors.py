"""Documents 域错误定义。"""

from __future__ import annotations

from typing import Any

from app.core.errors.exceptions import AppException

_STATUS_BY_CODE = {
    "VALIDATION_ERROR": 422,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "INVALID_STATE_TRANSITION": 409,
}


class DomainError(AppException):
    """可由平台全局异常处理器直接序列化的文档领域错误。"""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        field_errors: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=_STATUS_BY_CODE.get(code, 400),
            details=details,
            field_errors=field_errors,
        )


def not_found(message: str = "资源不存在", **details: Any) -> DomainError:
    return DomainError(code="NOT_FOUND", message=message, details=details)


def conflict(message: str, **details: Any) -> DomainError:
    return DomainError(code="CONFLICT", message=message, details=details)


def validation_error(message: str, field_errors: list[dict[str, str]] | None = None) -> DomainError:
    return DomainError(
        code="VALIDATION_ERROR",
        message=message,
        field_errors=field_errors or [],
    )


def invalid_transition(current: str, allowed: list[str]) -> DomainError:
    return DomainError(
        code="INVALID_STATE_TRANSITION",
        message="当前状态不允许该操作",
        details={"currentStatus": current, "allowedActions": allowed},
    )
