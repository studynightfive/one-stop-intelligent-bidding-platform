"""用户管理API路由.

实现用户管理相关接口：
- GET /users - 用户列表
- POST /users/invitations - 邀请用户
- POST /users/{userId}/invitations/resend - 重发邀请
- PATCH /users/{userId} - 修改用户
- POST /users/{userId}/status - 启停用户
- POST /users/{userId}/password-reset-email - 发送密码重置邮件
- GET /users/{userId}/projects - 用户项目列表
- GET /users/{userId}/activity - 用户活动记录
- GET /roles - 角色定义
- GET /permissions/matrix - 权限矩阵
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import AdminUser, AuthenticatedUser, DBSession
from app.core.errors import NotFoundError, ValidationError
from app.domains.auth.models.user import UserRole, UserStatus
from app.domains.auth.schemas.auth import (
    InvitationResponse,
    PermissionMatrix,
    RoleDefinition,
    SendInvitationResponse,
    SendPasswordResetEmailResponse,
    UpdateProfileRequest,
    UserActivityResponse,
    UserListResponse,
    UserProjectsResponse,
    UserResponse,
    UserStatusRequest,
)
from app.domains.auth.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["用户管理"])
metadata_router = APIRouter(tags=["用户管理"])


def _user_to_response(user: Any) -> UserResponse:
    """将User模型转换为响应模型."""
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        name=user.name,
        phone=user.phone,
        role=user.role.value,
        department=user.department,
        status=user.status.value,
        project_count=0,
        last_login_at=user.last_login_at,
        version=1,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get(
    "",
    response_model=UserListResponse,
    summary="用户列表",
    description="获取租户下的用户列表，支持分页和筛选。",
    responses={
        200: {"description": "成功"},
        403: {"description": "需要管理员权限"},
    },
)
async def list_users(
    current_user: AdminUser,
    db: DBSession,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: str | None = Query(None, description="搜索关键词"),
    role: str | None = Query(None, description="角色筛选"),
    department: str | None = Query(None, description="部门筛选"),
    user_status: str | None = Query(None, alias="status", description="状态筛选"),
) -> UserListResponse:
    """获取用户列表."""
    user_service = UserService(db)

    # 转换role和status
    role_enum = UserRole(role) if role else None
    status_enum = UserStatus(user_status) if user_status else None

    users, total = await user_service.list_users(
        tenant_id=UUID(current_user["tenant_id"]),
        page=page,
        page_size=page_size,
        keyword=keyword,
        role=role_enum,
        department=department,
        status=status_enum,
    )

    return UserListResponse(
        users=[_user_to_response(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/invitations",
    response_model=InvitationResponse,
    summary="邀请用户",
    description="创建新用户邀请，发送邀请邮件。",
    responses={
        200: {"description": "邀请成功"},
        403: {"description": "需要管理员权限"},
        400: {"description": "邮箱已被使用"},
    },
)
async def invite_user(
    request: dict[str, Any],
    current_user: AdminUser,
    db: DBSession,
) -> InvitationResponse:
    """邀请新用户."""
    user_service = UserService(db)

    try:
        user = await user_service.create_user(
            tenant_id=UUID(current_user["tenant_id"]),
            email=request["email"],
            name=request["name"],
            role=UserRole(request["role"]) if request.get("role") else UserRole.MEMBER,
            department=request.get("department", ""),
            phone=request.get("phone"),
            invited_by=UUID(current_user["id"]),
        )

        return InvitationResponse(
            user=_user_to_response(user),
            invitation_expires_at=user.created_at,  # TODO: 计算过期时间
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict(),
        ) from e


@router.post(
    "/{user_id}/invitations/resend",
    response_model=SendInvitationResponse,
    summary="重发邀请",
    description="重新发送用户邀请邮件。",
    responses={
        200: {"description": "发送成功"},
        403: {"description": "需要管理员权限"},
        404: {"description": "用户不存在"},
    },
)
async def resend_invitation(
    user_id: UUID,
    current_user: AdminUser,
    db: DBSession,
) -> SendInvitationResponse:
    """重发邀请."""
    # TODO: 实现重发邀请逻辑
    return SendInvitationResponse(sent=True)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="修改用户",
    description="修改用户信息。",
    responses={
        200: {"description": "成功"},
        403: {"description": "需要管理员权限"},
        404: {"description": "用户不存在"},
    },
)
async def update_user(
    user_id: UUID,
    request: UpdateProfileRequest,
    current_user: AdminUser,
    db: DBSession,
) -> UserResponse:
    """修改用户信息."""
    user_service = UserService(db)

    try:
        user = await user_service.update_user(
            user_id=user_id,
            name=request.name,
            phone=request.phone,
            department=request.department,
            role=UserRole(request.dict(exclude_unset=True).get("role", ""))
            if request.dict(exclude_unset=True).get("role")
            else None,
        )
        return _user_to_response(user)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.to_dict(),
        ) from e


@router.post(
    "/{user_id}/status",
    response_model=UserResponse,
    summary="启停用户",
    description="启用或禁用用户账号。",
    responses={
        200: {"description": "成功"},
        403: {"description": "需要管理员权限"},
        404: {"description": "用户不存在"},
    },
)
async def set_user_status(
    user_id: UUID,
    request: UserStatusRequest,
    current_user: AdminUser,
    db: DBSession,
) -> UserResponse:
    """启停用户."""
    user_service = UserService(db)

    try:
        user = await user_service.set_user_status(
            user_id=user_id,
            status=UserStatus(request.status),
            reason=request.reason,
        )
        return _user_to_response(user)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.to_dict(),
        ) from e


@router.post(
    "/{user_id}/password-reset-email",
    response_model=SendPasswordResetEmailResponse,
    summary="发送密码重置邮件",
    description="向用户发送密码重置邮件。",
    responses={
        200: {"description": "发送成功"},
        403: {"description": "需要管理员权限"},
        404: {"description": "用户不存在"},
    },
)
async def send_password_reset_email(
    user_id: UUID,
    current_user: AdminUser,
    db: DBSession,
) -> SendPasswordResetEmailResponse:
    """发送密码重置邮件."""
    # TODO: 实现发送密码重置邮件逻辑
    return SendPasswordResetEmailResponse(sent=True)


@router.get(
    "/{user_id}/projects",
    response_model=UserProjectsResponse,
    summary="用户项目列表",
    description="获取用户参与的项目列表。",
    responses={
        200: {"description": "成功"},
        403: {"description": "需要管理员权限或本人"},
    },
)
async def get_user_projects(
    user_id: UUID,
    current_user: AuthenticatedUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> UserProjectsResponse:
    """获取用户项目列表."""
    # TODO: 实现查询用户项目列表逻辑
    return UserProjectsResponse(
        projects=[],
        total=0,
        page=page,
    )


@router.get(
    "/{user_id}/activity",
    response_model=UserActivityResponse,
    summary="用户活动记录",
    description="获取用户的活动记录。",
    responses={
        200: {"description": "成功"},
        403: {"description": "需要管理员权限或本人"},
    },
)
async def get_user_activity(
    user_id: UUID,
    current_user: AuthenticatedUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> UserActivityResponse:
    """获取用户活动记录."""
    # TODO: 实现查询用户活动记录逻辑
    return UserActivityResponse(
        activities=[],
        total=0,
        page=page,
    )


# === 角色和权限 ===


@metadata_router.get(
    "/roles",
    response_model=list[RoleDefinition],
    summary="角色定义",
    description="获取系统中定义的所有角色及其权限。",
    responses={
        200: {"description": "成功"},
        403: {"description": "需要管理员权限"},
    },
)
async def list_roles(
    current_user: AdminUser,
    db: DBSession,
) -> list[RoleDefinition]:
    """获取角色定义列表."""
    # 角色定义（硬编码，可扩展为数据库存储）
    roles = [
        {
            "role": "admin",
            "label": "管理员",
            "description": "系统管理员，拥有所有权限",
            "permissions": [
                "users:read",
                "users:write",
                "users:delete",
                "projects:read",
                "projects:write",
                "projects:delete",
                "bids:read",
                "bids:write",
                "bids:review",
                "settings:read",
                "settings:write",
                "audit:read",
                "audit:export",
            ],
        },
        {
            "role": "project_lead",
            "label": "项目负责人",
            "description": "负责项目管理和评审",
            "permissions": [
                "projects:read",
                "projects:write",
                "bids:read",
                "bids:write",
                "bids:review",
                "users:read",
            ],
        },
        {
            "role": "reviewer",
            "label": "评审员",
            "description": "参与评审工作",
            "permissions": [
                "projects:read",
                "bids:read",
                "bids:review",
            ],
        },
        {
            "role": "member",
            "label": "成员",
            "description": "普通成员，可参与项目",
            "permissions": [
                "projects:read",
                "bids:read",
            ],
        },
    ]

    # TODO: 查询每个角色的用户数量
    return [RoleDefinition(**role, user_count=0) for role in roles]


@metadata_router.get(
    "/permissions/matrix",
    response_model=PermissionMatrix,
    summary="权限矩阵",
    description="获取完整的权限矩阵，展示各角色在不同模块的权限。",
    responses={
        200: {"description": "成功"},
        403: {"description": "需要管理员权限"},
    },
)
async def get_permissions_matrix(
    current_user: AdminUser,
) -> PermissionMatrix:
    """获取权限矩阵."""
    # 模块和权限定义
    modules = [
        {
            "module": "users",
            "label": "用户管理",
            "permissions": [
                {"key": "users:read", "label": "查看用户"},
                {"key": "users:write", "label": "管理用户"},
                {"key": "users:delete", "label": "删除用户"},
            ],
            "roles": {
                "admin": ["users:read", "users:write", "users:delete"],
                "project_lead": ["users:read"],
                "reviewer": [],
                "member": [],
            },
        },
        {
            "module": "projects",
            "label": "项目管理",
            "permissions": [
                {"key": "projects:read", "label": "查看项目"},
                {"key": "projects:write", "label": "管理项目"},
                {"key": "projects:delete", "label": "删除项目"},
            ],
            "roles": {
                "admin": ["projects:read", "projects:write", "projects:delete"],
                "project_lead": ["projects:read", "projects:write"],
                "reviewer": ["projects:read"],
                "member": ["projects:read"],
            },
        },
        {
            "module": "bids",
            "label": "投标管理",
            "permissions": [
                {"key": "bids:read", "label": "查看投标"},
                {"key": "bids:write", "label": "管理投标"},
                {"key": "bids:review", "label": "评审投标"},
            ],
            "roles": {
                "admin": ["bids:read", "bids:write", "bids:review"],
                "project_lead": ["bids:read", "bids:write", "bids:review"],
                "reviewer": ["bids:read", "bids:review"],
                "member": ["bids:read"],
            },
        },
        {
            "module": "settings",
            "label": "系统设置",
            "permissions": [
                {"key": "settings:read", "label": "查看设置"},
                {"key": "settings:write", "label": "修改设置"},
            ],
            "roles": {
                "admin": ["settings:read", "settings:write"],
                "project_lead": [],
                "reviewer": [],
                "member": [],
            },
        },
        {
            "module": "audit",
            "label": "审计日志",
            "permissions": [
                {"key": "audit:read", "label": "查看审计"},
                {"key": "audit:export", "label": "导出审计"},
            ],
            "roles": {
                "admin": ["audit:read", "audit:export"],
                "project_lead": [],
                "reviewer": [],
                "member": [],
            },
        },
        {
            "module": "files",
            "label": "文件管理",
            "permissions": [
                {"key": "files:upload", "label": "上传文件"},
                {"key": "files:download", "label": "下载文件"},
                {"key": "files:delete", "label": "删除文件"},
            ],
            "roles": {
                "admin": ["files:upload", "files:download", "files:delete"],
                "project_lead": ["files:upload", "files:download"],
                "reviewer": ["files:upload", "files:download"],
                "member": ["files:upload", "files:download"],
            },
        },
    ]

    return PermissionMatrix(modules=modules)
