"""依赖注入模块.

提供FastAPI依赖函数，用于认证、授权、数据库会话等。
"""

from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Annotated, Any
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import TokenRevokedError
from app.core.security.jwt import decode_token_unsafe, verify_token

# === 安全方案 ===
bearer_scheme = HTTPBearer(auto_error=False)


# === 类型别名 ===
CurrentUser = dict[str, Any]
DbSession = AsyncSession


# === 认证依赖 ===


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    db: Annotated[AsyncSession | None, Depends(get_db)] = None,
) -> CurrentUser:
    """获取当前认证用户.

    从Authorization头提取Bearer Token并验证。

    Args:
        credentials: HTTP Bearer凭证
        db: 数据库会话

    Returns:
        用户信息字典，包含id、tenant_id、role等

    Raises:
        HTTPException: Token无效或缺失
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHENTICATED", "message": "请先登录"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # 先解码 token（不验证签名）检查黑名单
        payload_unsafe = decode_token_unsafe(credentials.credentials)
        jti = payload_unsafe.get("jti")

        if jti:
            from app.core.redis import is_token_blacklisted

            if await is_token_blacklisted(jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "TOKEN_REVOKED", "message": "Token已被撤销，请重新登录"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # 验证 token 签名
        payload = verify_token(credentials.credentials, token_type="access")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHENTICATED", "message": "无效的Token"},
            )

        token_tenant_id = payload.get("tenant_id")
        token_role = payload.get("role", "member")
        user_name: str | None = None
        user_email: str | None = None
        if not token_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHENTICATED", "message": "Token缺少租户信息"},
            )

        # FastAPI 请求会注入数据库会话；直接调用该函数的轻量单元测试仍可只验证 JWT。
        if db is not None:
            from app.domains.auth.models.user import User, UserStatus

            try:
                normalized_user_id = UUID(str(user_id))
                normalized_tenant_id = UUID(str(token_tenant_id))
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "UNAUTHENTICATED", "message": "Token身份信息无效"},
                ) from exc

            result = await db.execute(
                select(User).where(
                    User.id == normalized_user_id,
                    User.tenant_id == normalized_tenant_id,
                    User.deleted_at.is_(None),
                )
            )
            user = result.scalar_one_or_none()
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "UNAUTHENTICATED", "message": "用户不存在或已被删除"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if user.status != UserStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "ACCOUNT_DISABLED", "message": "账号尚未激活或已被禁用"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            token_role = user.role.value
            user_name = user.name
            user_email = user.email
        else:
            user_name = payload.get("name")
            user_email = payload.get("email")

        return {
            "id": user_id,
            "tenant_id": token_tenant_id,
            "role": token_role,
            "status": "active",
            "name": user_name,
            "email": user_email,
            "jti": jti,  # 保存 jti 供 logout 使用
        }

    except HTTPException:
        raise
    except TokenRevokedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_REVOKED", "message": "Token已被撤销，请重新登录"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED" if "expired" in str(e).lower() else "UNAUTHENTICATED", "message": str(e)},
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_active_user(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """获取当前活跃用户.

    验证用户账号未被禁用。

    Args:
        current_user: 当前用户

    Returns:
        用户信息

    Raises:
        HTTPException: 用户已被禁用
    """
    if current_user.get("status") not in (None, "active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ACCOUNT_DISABLED", "message": "账号尚未激活或已被禁用"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_portal_user(
    portal_token: Annotated[str | None, Cookie()] = None,
) -> CurrentUser:
    """获取当前供应商Portal用户.

    从Cookie提取Portal Token并验证。

    Args:
        portal_token: Portal Token Cookie

    Returns:
        供应商信息字典

    Raises:
        HTTPException: Token无效或缺失
    """
    if portal_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHENTICATED", "message": "请先访问供应商门户"},
        )

    try:
        payload = verify_token(portal_token, token_type="portal")
        return {
            "id": payload.get("sub"),
            "supplier_id": payload.get("supplier_id"),
            "evaluation_id": payload.get("evaluation_id"),
            "type": "supplier",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Portal会话已过期，请重新获取链接"},
        ) from exc


# === 授权依赖 ===


async def require_admin(
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
) -> CurrentUser:
    """要求当前用户是管理员.

    Args:
        current_user: 当前用户

    Returns:
        用户信息

    Raises:
        HTTPException: 非管理员
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "此操作需要管理员权限"},
        )
    return current_user


async def require_project_lead_or_admin(
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
) -> CurrentUser:
    """要求当前用户是项目负责人或管理员.

    Args:
        current_user: 当前用户

    Returns:
        用户信息
    """
    if current_user.get("role") not in ("admin", "project_lead"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "此操作需要项目负责人或管理员权限"},
        )
    return current_user


async def require_reviewer_or_admin(
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
) -> CurrentUser:
    """要求当前用户是审核员或管理员.

    Args:
        current_user: 当前用户

    Returns:
        用户信息
    """
    if current_user.get("role") not in ("admin", "project_lead", "reviewer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "此操作需要审核员或管理员权限"},
        )
    return current_user


def require_role(*allowed_roles: str) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    """创建角色检查依赖.

    Args:
        allowed_roles: 允许的角色列表

    Returns:
        依赖函数
    """

    async def role_checker(
        current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    ) -> CurrentUser:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"此操作需要以下角色之一: {', '.join(allowed_roles)}",
                },
            )
        return current_user

    return role_checker


# === 数据库依赖 ===


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖函数（别名）."""
    async for session in get_db():
        yield session


# === 常用依赖类型 ===

# 已认证用户
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_active_user)]

# 管理员
AdminUser = Annotated[CurrentUser, Depends(require_admin)]

# 项目负责人或管理员
ProjectLeadOrAdmin = Annotated[CurrentUser, Depends(require_project_lead_or_admin)]

# 审核员或管理员
ReviewerOrAdmin = Annotated[CurrentUser, Depends(require_reviewer_or_admin)]

# 数据库会话
DBSession = Annotated[AsyncSession, Depends(get_db)]

# 可选认证用户
OptionalUser = Annotated[CurrentUser | None, Depends(get_current_user)]
