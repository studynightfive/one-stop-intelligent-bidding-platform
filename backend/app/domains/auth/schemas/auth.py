"""认证相关Pydantic schemas.

定义API请求和响应的数据模型。
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# === 请求模型 ===

class LoginRequest(BaseModel):
    """登录请求."""
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, description="密码")

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("密码不能为空")
        return v


class RegisterRequest(BaseModel):
    """注册请求（用于初始化第一个管理员用户）."""
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    name: str = Field(..., min_length=1, max_length=100, description="姓名")
    company_name: str = Field(..., min_length=1, max_length=200, description="公司名称")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("密码必须包含大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("密码必须包含小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码必须包含数字")
        return v


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求."""
    email: EmailStr = Field(..., description="邮箱")


class ResetPasswordRequest(BaseModel):
    """重置密码请求."""
    reset_token: str = Field(..., description="重置Token")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("密码必须包含大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("密码必须包含小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码必须包含数字")
        return v


class UpdateProfileRequest(BaseModel):
    """更新个人资料请求."""
    name: str | None = Field(None, min_length=1, max_length=100, description="姓名")
    phone: str | None = Field(None, max_length=20, description="电话号码")
    department: str | None = Field(None, max_length=100, description="部门")


# === 响应模型 ===

class UserResponse(BaseModel):
    """用户信息响应."""
    id: UUID = Field(..., description="用户ID")
    tenant_id: UUID = Field(..., description="租户ID")
    email: str = Field(..., description="邮箱")
    name: str = Field(..., description="姓名")
    phone: str | None = Field(None, description="电话")
    role: str = Field(..., description="角色")
    department: str = Field(..., description="部门")
    status: str = Field(..., description="状态")
    project_count: int = Field(default=0, description="参与项目数")
    last_login_at: datetime | None = Field(None, description="最后登录时间")
    version: int = Field(..., description="版本号")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class AuthSession(BaseModel):
    """认证会话响应."""
    access_token: str = Field(..., description="访问Token")
    access_token_expires_at: datetime = Field(..., description="Access Token过期时间")
    user: UserResponse = Field(..., description="用户信息")
    permissions: list[str] = Field(default_factory=list, description="权限列表")


class TokenResponse(BaseModel):
    """Token刷新响应."""
    access_token: str = Field(..., description="新的访问Token")
    refresh_token: str = Field(..., description="新的刷新Token")
    token_type: str = Field(default="Bearer", description="Token类型")
    expires_in: int = Field(..., description="Access Token有效期(秒)")


class LogoutResponse(BaseModel):
    """登出响应."""
    logged_out: bool = Field(default=True, description="是否已登出")


class ForgotPasswordResponse(BaseModel):
    """忘记密码响应."""
    accepted: bool = Field(default=True, description="请求是否被接受")


class ResetPasswordResponse(BaseModel):
    """重置密码响应."""
    reset: bool = Field(default=True, description="是否已重置")


class UserListResponse(BaseModel):
    """用户列表响应."""
    users: list[UserResponse] = Field(..., description="用户列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")


class InvitationResponse(BaseModel):
    """邀请响应."""
    user: UserResponse = Field(..., description="被邀请的用户")
    invitation_expires_at: datetime = Field(..., description="邀请过期时间")


class SendInvitationResponse(BaseModel):
    """重发邀请响应."""
    sent: bool = Field(default=True, description="是否已发送")


class SendPasswordResetEmailResponse(BaseModel):
    """发送密码重置邮件响应."""
    sent: bool = Field(default=True, description="是否已发送")


class UserProjectsResponse(BaseModel):
    """用户项目列表响应."""
    projects: list[dict[str, Any]] = Field(default_factory=list, description="项目列表")
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="当前页")


class UserActivityResponse(BaseModel):
    """用户活动记录响应."""
    activities: list[dict[str, Any]] = Field(default_factory=list, description="活动列表")
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="当前页")


class RoleDefinition(BaseModel):
    """角色定义."""
    role: str = Field(..., description="角色标识")
    label: str = Field(..., description="角色名称")
    description: str = Field(..., description="角色描述")
    permissions: list[str] = Field(default_factory=list, description="权限列表")
    user_count: int = Field(default=0, description="用户数量")


class PermissionMatrix(BaseModel):
    """权限矩阵."""
    modules: list[dict[str, Any]] = Field(..., description="模块权限列表")


class UserStatusRequest(BaseModel):
    """修改用户状态请求."""
    status: str = Field(..., description="新状态")
    reason: str | None = Field(None, description="操作原因")
