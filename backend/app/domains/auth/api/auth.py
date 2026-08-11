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

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.dependencies import AuthenticatedUser, DBSession
from app.core.errors import (
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
)
from app.core.http import success_response
from app.domains.auth.mappers import ROLE_PERMISSIONS, user_to_data
from app.domains.auth.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
)
from app.domains.auth.services.auth_service import AuthService
from app.domains.auth.services.email_service import EmailService
from app.domains.auth.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["认证"])


def _auth_session(user: Any, tokens: dict[str, Any]) -> dict[str, Any]:
    role = user.role.value
    return {
        "accessToken": tokens["access_token"],
        "accessTokenExpiresAt": datetime.fromtimestamp(
            datetime.now(UTC).timestamp() + tokens["expires_in"],
            tz=UTC,
        ),
        "user": user_to_data(user),
        "permissions": ROLE_PERMISSIONS.get(role, []),
    }


@router.post(
    "/login",
    summary="用户登录",
    description="使用邮箱和密码登录，返回Access Token和用户信息。",
    responses={
        200: {"description": "登录成功"},
        401: {"description": "认证失败"},
    },
)
async def login(
    payload: LoginRequest,
    http_request: Request,
    db: DBSession,
) -> JSONResponse:
    """用户登录."""
    from app.core.config import settings

    auth_service = AuthService(db)

    try:
        user = await auth_service.authenticate(payload.email, payload.password)
        tokens = await auth_service.create_tokens(user)
        response = success_response(_auth_session(user, tokens), request=http_request)
        response.set_cookie(
            key=settings.refresh_token_cookie_name,
            value=tokens["refresh_token"],
            max_age=settings.refresh_token_cookie_max_age,
            secure=settings.refresh_token_cookie_secure,
            httponly=settings.refresh_token_cookie_http_only,
            samesite=settings.refresh_token_cookie_same_site,
        )

        return response
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.post(
    "/refresh",
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
) -> JSONResponse:
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

        if user is None:
            raise AuthenticationError(message="用户不存在或已被禁用")
        response = success_response(_auth_session(user, tokens), request=request)
        response.set_cookie(
            key=settings.refresh_token_cookie_name,
            value=tokens["refresh_token"],
            max_age=settings.refresh_token_cookie_max_age,
            secure=settings.refresh_token_cookie_secure,
            httponly=settings.refresh_token_cookie_http_only,
            samesite=settings.refresh_token_cookie_same_site,
        )
        return response
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
    summary="登出",
    description="使当前Token失效。",
    responses={
        200: {"description": "登出成功"},
        401: {"description": "未登录"},
    },
)
async def logout(
    request: Request,
    current_user: AuthenticatedUser,
) -> JSONResponse:
    """用户登出."""
    from app.core.config import settings
    from app.core.redis import add_token_to_blacklist

    # 将 Token 加入黑名单
    jti = current_user.get("jti")
    if jti:
        # 计算 Token 剩余有效期
        exp_seconds = settings.jwt_access_token_ttl_minutes * 60
        await add_token_to_blacklist(jti, exp_seconds)

    response = success_response({"loggedOut": True}, request=request)
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        secure=settings.refresh_token_cookie_secure,
        httponly=settings.refresh_token_cookie_http_only,
        samesite=settings.refresh_token_cookie_same_site,
    )

    return response


@router.get(
    "/me",
    summary="获取当前用户",
    description="获取当前登录用户的信息。",
    responses={
        200: {"description": "成功"},
        401: {"description": "未登录"},
    },
)
async def get_current_user_info(
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> JSONResponse:
    """获取当前用户信息."""
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(UUID(current_user["id"]))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "用户不存在"},
        )

    return success_response(user_to_data(user), request=request)


@router.patch(
    "/me",
    summary="更新个人资料",
    description="更新当前登录用户的个人资料。",
    responses={
        200: {"description": "更新成功"},
        401: {"description": "未登录"},
    },
)
async def update_profile(
    payload: UpdateProfileRequest,
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> JSONResponse:
    """更新个人资料."""
    user_service = UserService(db)
    user = await user_service.update_user(
        user_id=UUID(current_user["id"]),
        name=payload.name,
        phone=payload.phone,
        department=payload.department,
    )
    return success_response(user_to_data(user), request=request)


@router.post(
    "/password/forgot",
    summary="忘记密码",
    description="发送密码重置邮件。",
    responses={
        200: {"description": "请求已接受"},
    },
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: DBSession,
) -> JSONResponse:
    """忘记密码."""
    auth_service = AuthService(db)
    user = await auth_service.get_active_user_by_email(payload.email)
    if user is not None:
        token = auth_service.create_password_reset_token(user)
        await EmailService().send_password_reset(email=user.email, name=user.name, token=token)
    # 始终返回相同结果，避免暴露邮箱是否存在。
    return success_response({"accepted": True}, request=request)


@router.post(
    "/password/reset",
    summary="重置密码",
    description="使用重置Token设置新密码。",
    responses={
        200: {"description": "密码已重置"},
        400: {"description": "Token无效"},
    },
)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: DBSession,
) -> JSONResponse:
    """重置密码."""
    try:
        await AuthService(db).reset_password(payload.reset_token, payload.new_password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RESET_TOKEN", "message": exc.message},
        ) from exc
    return success_response({"reset": True}, request=request)
