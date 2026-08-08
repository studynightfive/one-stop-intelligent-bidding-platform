"""认证schemas模块."""

from app.domains.auth.schemas.auth import (
    AuthSession,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    InvitationResponse,
    # request
    LoginRequest,
    LogoutResponse,
    PermissionMatrix,
    RegisterRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    RoleDefinition,
    SendInvitationResponse,
    SendPasswordResetEmailResponse,
    TokenResponse,
    UpdateProfileRequest,
    UserActivityResponse,
    UserListResponse,
    UserProjectsResponse,
    # response
    UserResponse,
    UserStatusRequest,
)

__all__ = [
    # request
    "LoginRequest",
    "RegisterRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "UpdateProfileRequest",
    "UserStatusRequest",
    # response
    "UserResponse",
    "AuthSession",
    "TokenResponse",
    "LogoutResponse",
    "ForgotPasswordResponse",
    "ResetPasswordResponse",
    "UserListResponse",
    "InvitationResponse",
    "SendInvitationResponse",
    "SendPasswordResetEmailResponse",
    "UserProjectsResponse",
    "UserActivityResponse",
    "RoleDefinition",
    "PermissionMatrix",
]
