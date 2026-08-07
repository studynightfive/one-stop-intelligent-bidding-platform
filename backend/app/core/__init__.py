"""M4 公共平台后端 - core 模块."""

from app.core.config import settings
from app.core.database import get_db, async_engine, AsyncSessionLocal
from app.core.errors import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    ConflictError,
    DeadlinePassedError,
    InvalidStateTransitionError,
    FileRejectedError,
    VirusDetectedError,
    AiProviderUnavailableError,
    JobFailedError,
    InternalError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_password,
    get_password_hash,
)
from app.core.dependencies import get_current_user, get_current_active_user, require_admin

__all__ = [
    # config
    "settings",
    # database
    "get_db",
    "async_engine",
    "AsyncSessionLocal",
    # errors
    "AppException",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "DeadlinePassedError",
    "InvalidStateTransitionError",
    "FileRejectedError",
    "VirusDetectedError",
    "AiProviderUnavailableError",
    "JobFailedError",
    "InternalError",
    # security
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "verify_password",
    "get_password_hash",
    # dependencies
    "get_current_user",
    "get_current_active_user",
    "require_admin",
]
