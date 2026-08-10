"""M5 投标域错误。

领域错误继承平台 ``AppException``，由 M4 已注册的全局处理器输出统一错误
envelope；M5 不复制或改写平台异常处理逻辑。
"""

from __future__ import annotations

from typing import Any

from app.core.errors.exceptions import AppException

_STATUS_BY_CODE = {
    "VALIDATION_ERROR": 422,
    "UNAUTHENTICATED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "VERSION_CONFLICT": 409,
    "DEADLINE_PASSED": 409,
    "INVALID_STATE_TRANSITION": 409,
    "FILE_REJECTED": 422,
    "JOB_FAILED": 500,
}


class DomainError(AppException):
    """M5 可捕获且能被平台全局处理器识别的业务错误。"""

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


def validation_error(message: str, field_errors: list[dict[str, str]] | None = None) -> DomainError:
    return DomainError(
        code="VALIDATION_ERROR",
        message=message,
        field_errors=field_errors or [],
    )


def deadline_passed(message: str = "已过截止时间", **details: Any) -> DomainError:
    return DomainError(code="DEADLINE_PASSED", message=message, details=details)


def file_rejected(message: str = "文件被拒绝", **details: Any) -> DomainError:
    return DomainError(code="FILE_REJECTED", message=message, details=details)
