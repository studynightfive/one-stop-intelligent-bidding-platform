"""Authentication request schemas."""

from app.domains.auth.schemas.auth import (
    ForgotPasswordRequest,
    InviteUserRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UpdateUserRequest,
    UserStatusRequest,
)

__all__ = [
    "ForgotPasswordRequest",
    "InviteUserRequest",
    "LoginRequest",
    "RegisterRequest",
    "ResetPasswordRequest",
    "UpdateProfileRequest",
    "UpdateUserRequest",
    "UserStatusRequest",
]
