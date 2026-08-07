"""认证schemas模块."""

from app.domains.auth.schemas.auth import (
    # request
    LoginRequest,
    RegisterRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UserStatusRequest,
    # response
    UserResponse,
    AuthSession,
    TokenResponse,
    LogoutResponse,
    ForgotPasswordResponse,
    ResetPasswordResponse,
    UserListResponse,
    InvitationResponse,
    SendInvitationResponse,
    SendPasswordResetEmailResponse,
    UserProjectsResponse,
    UserActivityResponse,
    RoleDefinition,
    PermissionMatrix,
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
