"""认证API路由.

实现认证相关接口：
- POST /auth/login - 登录
- POST /auth/refresh - 刷新Token
- POST /auth/logout - 登出
- GET /auth/me - 获取当前用户
- PATCH /auth/me - 更新个人资料
- POST /auth/password/forgot - 忘记密码
- POST /auth/password/reset - 重置密码
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.dependencies import AuthenticatedUser, DBSession
from app.core.errors import (
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
)
from app.domains.auth.schemas.auth import (
    AuthSession,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app.domains.auth.services.auth_service import AuthService
from app.domains.auth.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["认证"])


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
        project_count=0,  # TODO: 从数据库查询
        last_login_at=user.last_login_at,
        version=1,  # TODO: 添加version字段
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post(
    "/login",
    response_model=AuthSession,
    summary="用户登录",
    description="使用邮箱和密码登录，返回Access Token和用户信息。",
    responses={
        200: {"description": "登录成功"},
        401: {"description": "认证失败"},
    },
)
async def login(
    request: LoginRequest,
    response: Response,
    db: DBSession,
) -> AuthSession:
    """用户登录."""
    from app.core.config import settings

    auth_service = AuthService(db)

    try:
        user = await auth_service.authenticate(request.email, request.password)
        tokens = await auth_service.create_tokens(user)
        user_response = _user_to_response(user)

        # 设置 Refresh Token Cookie
        response.set_cookie(
            key=settings.refresh_token_cookie_name,
            value=tokens["refresh_token"],
            max_age=settings.refresh_token_cookie_max_age,
            secure=settings.refresh_token_cookie_secure,
            httponly=settings.refresh_token_cookie_http_only,
            samesite=settings.refresh_token_cookie_same_site,
        )

        return AuthSession(
            access_token=tokens["access_token"],
            access_token_expires_at=datetime.fromtimestamp(
                datetime.now(UTC).timestamp() + tokens["expires_in"],
                tz=UTC,
            ),
            user=user_response,
            permissions=[],  # TODO: 从角色获取
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.post(
    "/refresh",
    response_model=AuthSession,
    summary="刷新Token",
    description="使用Refresh Token获取新的Access Token。",
    responses={
        200: {"description": "刷新成功"},
        401: {"description": "Token无效或过期"},
    },
)
async def refresh_token(
    request: Request,
    db: DBSession,
) -> AuthSession:
    """刷新Token."""
    from app.core.config import settings

    # 从Cookie获取Refresh Token
    refresh_token = request.cookies.get(settings.refresh_token_cookie_name)

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHENTICATED", "message": "请提供Refresh Token"},
        )

    auth_service = AuthService(db)

    try:
        tokens = await auth_service.refresh_tokens(refresh_token)
        user_id = UUID(tokens["user_id"])
        user = await auth_service.get_user_by_id(user_id)

        return AuthSession(
            access_token=tokens["access_token"],
            access_token_expires_at=datetime.fromtimestamp(
                datetime.now(UTC).timestamp() + tokens["expires_in"],
                tz=UTC,
            ),
            user=_user_to_response(user) if user else None,
            permissions=[],
        )
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Refresh Token已过期，请重新登录"},
        ) from exc
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="登出",
    description="使当前Token失效。",
    responses={
        200: {"description": "登出成功"},
        401: {"description": "未登录"},
    },
)
async def logout(
    current_user: AuthenticatedUser,
    response: Response,
) -> LogoutResponse:
    """用户登出."""
    from app.core.config import settings
    from app.core.redis import add_token_to_blacklist

    # 将 Token 加入黑名单
    jti = current_user.get("jti")
    if jti:
        # 计算 Token 剩余有效期
        exp_seconds = settings.jwt_access_token_ttl_minutes * 60
        await add_token_to_blacklist(jti, exp_seconds)

    # 清除 Refresh Token Cookie
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        secure=settings.refresh_token_cookie_secure,
        httponly=settings.refresh_token_cookie_http_only,
        samesite=settings.refresh_token_cookie_same_site,
    )

    return LogoutResponse(logged_out=True)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户",
    description="获取当前登录用户的信息。",
    responses={
        200: {"description": "成功"},
        401: {"description": "未登录"},
    },
)
async def get_current_user_info(
    current_user: AuthenticatedUser,
    db: DBSession,
) -> UserResponse:
    """获取当前用户信息."""
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(UUID(current_user["id"]))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "用户不存在"},
        )

    return _user_to_response(user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="更新个人资料",
    description="更新当前登录用户的个人资料。",
    responses={
        200: {"description": "更新成功"},
        401: {"description": "未登录"},
    },
)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> UserResponse:
    """更新个人资料."""
    user_service = UserService(db)
    user = await user_service.update_user(
        user_id=UUID(current_user["id"]),
        name=request.name,
        phone=request.phone,
        department=request.department,
    )
    return _user_to_response(user)


@router.post(
    "/password/forgot",
    response_model=ForgotPasswordResponse,
    summary="忘记密码",
    description="发送密码重置邮件。",
    responses={
        200: {"description": "请求已接受"},
    },
)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: DBSession,
) -> ForgotPasswordResponse:
    """忘记密码."""
    # TODO: 实现发送重置邮件逻辑
    # 1. 查询用户
    # 2. 生成重置Token
    # 3. 发送邮件
    return ForgotPasswordResponse(accepted=True)


@router.post(
    "/password/reset",
    response_model=ResetPasswordResponse,
    summary="重置密码",
    description="使用重置Token设置新密码。",
    responses={
        200: {"description": "密码已重置"},
        400: {"description": "Token无效"},
    },
)
async def reset_password(
    request: ResetPasswordRequest,
    db: DBSession,
) -> ResetPasswordResponse:
    """重置密码."""
    # TODO: 实现重置密码逻辑
    # 1. 验证Token
    # 2. 更新密码
    return ResetPasswordResponse(reset=True)
