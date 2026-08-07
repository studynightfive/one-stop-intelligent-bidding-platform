"""自定义异常类.

所有业务异常必须继承 AppException。
错误码定义见 PROJECT_MASTER_PROMPT.md 第7.1节。
"""

from typing import Any


class AppException(Exception):
    """应用基础异常类.

    所有业务异常必须继承此类。
    异常会被全局异常处理器捕获并转换为标准API响应。
    """

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
        field_errors: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.field_errors = field_errors or []

    def to_dict(self) -> dict[str, Any]:
        """转换为API响应格式."""
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        if self.field_errors:
            result["fieldErrors"] = self.field_errors
        return result


# === 认证相关异常 ===

class AuthenticationError(AppException):
    """认证失败异常 (401)."""

    def __init__(
        self,
        message: str = "认证失败，请重新登录",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="UNAUTHENTICATED",
            status_code=401,
            details=details,
        )


class TokenExpiredError(AuthenticationError):
    """Token过期异常 (401)."""

    def __init__(self, message: str = "Token已过期，请重新登录") -> None:
        super().__init__(
            message=message,
            details={"reason": "token_expired"},
        )


class InvalidCredentialsError(AuthenticationError):
    """无效凭证异常 (401)."""

    def __init__(self, message: str = "邮箱或密码错误") -> None:
        super().__init__(
            message=message,
            details={"reason": "invalid_credentials"},
        )


class TokenRevokedError(AuthenticationError):
    """Token已被撤销异常 (401)."""

    def __init__(self, message: str = "Token已被撤销，请重新登录") -> None:
        super().__init__(
            message=message,
            details={"reason": "token_revoked"},
        )


# === 授权相关异常 ===

class AuthorizationError(AppException):
    """权限不足异常 (403)."""

    def __init__(
        self,
        message: str = "权限不足，无法执行此操作",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
            details=details,
        )


class ForbiddenError(AuthorizationError):
    """禁止访问异常 (403)."""
    pass


# === 资源相关异常 ===

class NotFoundError(AppException):
    """资源不存在异常 (404)."""

    def __init__(
        self,
        message: str = "请求的资源不存在",
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        details = {}
        if resource_type:
            details["resourceType"] = resource_type
        if resource_id:
            details["resourceId"] = resource_id
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=details,
        )


# === 业务逻辑异常 ===

class ValidationError(AppException):
    """数据验证异常 (422)."""

    def __init__(
        self,
        message: str = "数据验证失败",
        field_errors: list[dict[str, str]] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            field_errors=field_errors,
            details=details,
        )


class ConflictError(AppException):
    """数据冲突异常 (409)."""

    def __init__(
        self,
        message: str = "数据冲突，请刷新后重试",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details=details,
        )


class VersionConflictError(ConflictError):
    """版本冲突异常 (409)."""

    def __init__(
        self,
        expected_version: int,
        actual_version: int,
    ) -> None:
        super().__init__(
            message="数据已被其他成员更新，请刷新后重试",
            details={
                "expectedVersion": expected_version,
                "actualVersion": actual_version,
            },
        )


class DeadlinePassedError(AppException):
    """截止时间已过异常 (400)."""

    def __init__(self, message: str = "已超过截止时间") -> None:
        super().__init__(
            message=message,
            code="DEADLINE_PASSED",
            status_code=400,
        )


class InvalidStateTransitionError(AppException):
    """无效状态转换异常 (409)."""

    def __init__(
        self,
        current_status: str,
        allowed_actions: list[str],
        details: dict[str, Any] | None = None,
    ) -> None:
        d = {"currentStatus": current_status, "allowedActions": allowed_actions}
        if details:
            d.update(details)
        super().__init__(
            message="当前状态不允许此操作",
            code="INVALID_STATE_TRANSITION",
            status_code=409,
            details=d,
        )


# === 文件相关异常 ===

class FileRejectedError(AppException):
    """文件被拒绝异常 (400)."""

    def __init__(
        self,
        message: str = "文件不符合要求",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="FILE_REJECTED",
            status_code=400,
            details=details,
        )


class FileTooLargeError(FileRejectedError):
    """文件过大异常."""

    def __init__(
        self,
        max_size: int,
        actual_size: int,
    ) -> None:
        super().__init__(
            message=f"文件大小超过限制（最大{max_size // (1024*1024)}MB）",
            details={
                "maxSizeBytes": max_size,
                "actualSizeBytes": actual_size,
            },
        )


class UnsupportedFileTypeError(FileRejectedError):
    """不支持的文件类型异常."""

    def __init__(
        self,
        file_extension: str,
        allowed_extensions: list[str],
    ) -> None:
        super().__init__(
            message=f"不支持的文件类型: {file_extension}",
            details={
                "fileExtension": file_extension,
                "allowedExtensions": allowed_extensions,
            },
        )


class VirusDetectedError(AppException):
    """文件包含病毒异常 (400)."""

    def __init__(
        self,
        file_name: str,
        message: str = "文件安全检查未通过，请重新上传",
    ) -> None:
        super().__init__(
            message=message,
            code="VIRUS_DETECTED",
            status_code=400,
            details={"fileName": file_name},
        )


# === AI相关异常 ===

class AiProviderUnavailableError(AppException):
    """AI服务不可用异常 (503)."""

    def __init__(
        self,
        provider: str,
        message: str | None = None,
    ) -> None:
        super().__init__(
            message=message or f"AI服务暂时不可用: {provider}",
            code="AI_PROVIDER_UNAVAILABLE",
            status_code=503,
            details={"provider": provider},
        )


class JobFailedError(AppException):
    """任务执行失败异常 (500)."""

    def __init__(
        self,
        job_id: str,
        message: str = "任务执行失败",
        details: dict[str, Any] | None = None,
    ) -> None:
        d = {"jobId": job_id}
        if details:
            d.update(details)
        super().__init__(
            message=message,
            code="JOB_FAILED",
            status_code=500,
            details=d,
        )


# === 速率限制异常 ===

class RateLimitedError(AppException):
    """请求过于频繁异常 (429)."""

    def __init__(
        self,
        message: str = "请求过于频繁，请稍后再试",
        retry_after: int | None = None,
    ) -> None:
        details = {}
        if retry_after:
            details["retryAfterSeconds"] = retry_after
        super().__init__(
            message=message,
            code="RATE_LIMITED",
            status_code=429,
            details=details,
        )


# === 内部错误 ===

class InternalError(AppException):
    """内部服务器错误 (500)."""

    def __init__(
        self,
        message: str = "服务器内部错误",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="INTERNAL_ERROR",
            status_code=500,
            details=details,
        )
