"""错误处理模块."""

from app.core.errors.exceptions import (
    AppException,
    AuthenticationError,
    TokenExpiredError,
    InvalidCredentialsError,
    TokenRevokedError,
    AuthorizationError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
    ConflictError,
    VersionConflictError,
    DeadlinePassedError,
    InvalidStateTransitionError,
    FileRejectedError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    VirusDetectedError,
    AiProviderUnavailableError,
    JobFailedError,
    RateLimitedError,
    InternalError,
)
from app.core.errors.handlers import register_exception_handlers

__all__ = [
    # exceptions
    "AppException",
    "AuthenticationError",
    "TokenExpiredError",
    "InvalidCredentialsError",
    "TokenRevokedError",
    "AuthorizationError",
    "ForbiddenError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "VersionConflictError",
    "DeadlinePassedError",
    "InvalidStateTransitionError",
    "FileRejectedError",
    "FileTooLargeError",
    "UnsupportedFileTypeError",
    "VirusDetectedError",
    "AiProviderUnavailableError",
    "JobFailedError",
    "RateLimitedError",
    "InternalError",
    # handlers
    "register_exception_handlers",
]
