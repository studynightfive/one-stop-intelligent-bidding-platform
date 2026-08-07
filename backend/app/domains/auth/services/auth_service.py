"""认证服务.

提供用户注册、登录、Token刷新等认证功能。
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
    ValidationError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.domains.auth.models.user import User, UserRole, UserStatus


class AuthService:
    """认证服务."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate(self, email: str, password: str) -> User:
        """验证用户凭证.

        Args:
            email: 邮箱
            password: 明文密码

        Returns:
            用户对象

        Raises:
            InvalidCredentialsError: 凭证无效
        """
        # 查询用户
        stmt = select(User).where(
            User.email == email,
            User.status == UserStatus.ACTIVE,
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.password_hash:
            raise InvalidCredentialsError()

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        # 更新最后登录时间
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()

        return user

    async def create_tokens(self, user: User) -> dict[str, Any]:
        """为用户创建Access和Refresh Token.

        Args:
            user: 用户对象

        Returns:
            包含token信息的字典
        """
        # Access Token声明
        access_claims = {
            "tenant_id": str(user.tenant_id),
            "role": user.role.value,
        }

        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=settings.jwt_access_token_ttl_minutes),
            additional_claims=access_claims,
        )

        refresh_token = create_refresh_token(
            subject=str(user.id),
            expires_delta=timedelta(days=settings.jwt_refresh_token_ttl_days),
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": settings.jwt_access_token_ttl_minutes * 60,
        }

    async def refresh_tokens(self, refresh_token: str) -> dict[str, Any]:
        """刷新Token.

        Args:
            refresh_token: Refresh Token

        Returns:
            包含token信息和用户ID的字典

        Raises:
            TokenExpiredError: Token已过期
            AuthenticationError: Token无效
        """
        try:
            payload = verify_token(refresh_token, token_type="refresh")
        except Exception as e:
            if "expired" in str(e).lower():
                raise TokenExpiredError()
            raise AuthenticationError(message="无效的Refresh Token")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError(message="无效的Refresh Token")

        # 查询用户
        stmt = select(User).where(
            User.id == UUID(user_id),
            User.status == UserStatus.ACTIVE,
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError(message="用户不存在或已被禁用")

        # 生成新Token
        tokens = await self.create_tokens(user)
        tokens["user_id"] = user_id  # 返回用户ID供调用方使用
        return tokens

    async def register(
        self,
        email: str,
        password: str,
        name: str,
        tenant_id: UUID,
        role: UserRole = UserRole.MEMBER,
        department: str = "",
        phone: str | None = None,
    ) -> User:
        """注册新用户.

        Args:
            email: 邮箱
            password: 密码
            name: 姓名
            tenant_id: 租户ID
            role: 角色，默认MEMBER
            department: 部门
            phone: 电话

        Returns:
            新创建的用户对象

        Raises:
            ValidationError: 邮箱已被使用
        """
        # 检查邮箱唯一性
        stmt = select(User).where(
            User.tenant_id == tenant_id,
            User.email == email,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            raise ValidationError(
                message="该邮箱已被注册",
                field_errors=[{
                    "field": "email",
                    "code": "duplicate",
                    "message": "该邮箱已被注册",
                }],
            )

        # 创建用户
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            name=name,
            tenant_id=tenant_id,
            role=role,
            department=department,
            phone=phone,
            status=UserStatus.ACTIVE,  # 直接激活
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """根据ID获取用户.

        Args:
            user_id: 用户ID

        Returns:
            用户对象或None
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str, tenant_id: UUID) -> User | None:
        """根据邮箱获取用户.

        Args:
            email: 邮箱
            tenant_id: 租户ID

        Returns:
            用户对象或None
        """
        stmt = select(User).where(
            User.email == email,
            User.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
