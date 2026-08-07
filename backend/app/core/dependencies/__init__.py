"""依赖注入模块.

提供FastAPI依赖函数，用于认证、授权、数据库会话等。
"""

from typing import Annotated, Any

from fastapi import Cookie, Depends, Header, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import (
    AuthenticationError,
    AuthorizationError,
    TokenRevokedError,
)
from app.core.security.jwt import decode_token_unsafe, verify_token


# === 安全方案 ===
bearer_scheme = HTTPBearer(auto_error=False)


# === 类型别名 ===
CurrentUser = dict[str, Any]
DbSession = AsyncSession


# === 认证依赖 ===

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
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

        # TODO: 从数据库加载用户信息，验证用户状态
        # 目前返回payload中的信息
        return {
            "id": user_id,
            "tenant_id": payload.get("tenant_id"),
            "role": payload.get("role", "member"),
            "jti": jti,  # 保存 jti 供 logout 使用
        }

    except TokenRevokedError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_REVOKED", "message": "Token已被撤销，请重新登录"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED" if "expired" in str(e).lower() else "UNAUTHENTICATED", "message": str(e)},
            headers={"WWW-Authenticate": "Bearer"},
        )


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
    # TODO: 从数据库检查用户状态是否为active
    # if current_user.get("status") == "disabled":
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail={"code": "ACCOUNT_DISABLED", "message": "账号已被禁用"},
    #     )
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
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Portal会话已过期，请重新获取链接"},
        )


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


def require_role(*allowed_roles: str):
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

async def get_db_session() -> AsyncSession:
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
