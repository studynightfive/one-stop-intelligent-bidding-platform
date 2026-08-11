"""用户服务.

提供用户管理功能。
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.core.security import create_action_token
from app.domains.auth.models.user import User, UserRole, UserStatus


class UserService:
    """用户服务."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(
        self,
        user_id: UUID,
        include_deleted: bool = False,
        tenant_id: UUID | None = None,
    ) -> User | None:
        """根据ID获取用户.

        Args:
            user_id: 用户ID
            include_deleted: 是否包含已删除用户

        Returns:
            用户对象或None
        """
        stmt = select(User).where(User.id == user_id)
        if tenant_id is not None:
            stmt = stmt.where(User.tenant_id == tenant_id)
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
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
            User.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_users(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        role: UserRole | None = None,
        department: str | None = None,
        status: UserStatus | None = None,
        sort_by: str = "createdAt",
        sort_order: str = "desc",
    ) -> tuple[list[User], int]:
        """分页查询用户列表.

        Args:
            tenant_id: 租户ID
            page: 页码（从1开始）
            page_size: 每页数量
            keyword: 搜索关键词（姓名/邮箱）
            role: 角色筛选
            department: 部门筛选
            status: 状态筛选
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            (用户列表, 总数)
        """
        # 基础查询
        stmt = select(User).where(
            User.tenant_id == tenant_id,
            User.deleted_at.is_(None),
        )

        # 关键词筛选
        if keyword:
            stmt = stmt.where(User.name.ilike(f"%{keyword}%") | User.email.ilike(f"%{keyword}%"))

        # 其他筛选
        if role:
            stmt = stmt.where(User.role == role)
        if department:
            stmt = stmt.where(User.department == department)
        if status:
            stmt = stmt.where(User.status == status)

        # 计算总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        sort_columns = {
            "createdAt": User.created_at,
            "name": User.name,
            "email": User.email,
        }
        sort_column = sort_columns.get(sort_by, User.created_at)
        order_expression = sort_column.asc() if sort_order == "asc" else sort_column.desc()
        stmt = stmt.order_by(order_expression).offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        users = list(result.scalars().all())

        return users, total

    async def create_user(
        self,
        tenant_id: UUID,
        email: str,
        name: str,
        role: UserRole = UserRole.MEMBER,
        department: str = "",
        phone: str | None = None,
        send_invitation: bool = True,
        invited_by: UUID | None = None,
    ) -> User:
        """创建新用户（邀请）.

        Args:
            tenant_id: 租户ID
            email: 邮箱
            name: 姓名
            role: 角色
            department: 部门
            phone: 电话
            send_invitation: 是否发送邀请邮件
            invited_by: 邀请人ID

        Returns:
            新创建的用户对象

        Raises:
            ValidationError: 邮箱已被使用
        """
        # 检查邮箱唯一性
        existing = await self.get_user_by_email(email, tenant_id)
        if existing:
            raise ValidationError(
                message="该邮箱已被注册",
                field_errors=[
                    {
                        "field": "email",
                        "code": "duplicate",
                        "message": "该邮箱已被注册",
                    }
                ],
            )

        # 创建用户（初始状态为invited）
        user = User(
            tenant_id=tenant_id,
            email=email,
            name=name,
            role=role,
            department=department,
            phone=phone,
            status=UserStatus.INVITED,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    @staticmethod
    def create_invitation_token(user: User) -> tuple[str, datetime]:
        """Create a 24-hour invitation token tied to the current user version."""
        expires_at = datetime.now(UTC) + timedelta(hours=24)
        token = create_action_token(
            str(user.id),
            token_type="invitation",
            expires_delta=timedelta(hours=24),
            additional_claims={
                "tenant_id": str(user.tenant_id),
                "credential_version": user.updated_at.isoformat(),
            },
        )
        return token, expires_at

    async def get_invited_user(self, user_id: UUID, tenant_id: UUID) -> User:
        """Return an invited user within the caller tenant."""
        user = await self.get_user_by_id(user_id, tenant_id=tenant_id)
        if user is None or user.status != UserStatus.INVITED:
            raise NotFoundError(resource_type="invitation", resource_id=str(user_id))
        return user

    async def count_users_by_role(self, tenant_id: UUID) -> dict[UserRole, int]:
        """Return live role totals for role metadata."""
        result = await self.db.execute(
            select(User.role, func.count(User.id))
            .where(User.tenant_id == tenant_id, User.deleted_at.is_(None))
            .group_by(User.role)
        )
        return {role: count for role, count in result.all()}

    async def update_user(
        self,
        user_id: UUID,
        name: str | None = None,
        phone: str | None = None,
        department: str | None = None,
        role: UserRole | None = None,
        tenant_id: UUID | None = None,
    ) -> User:
        """更新用户信息.

        Args:
            user_id: 用户ID
            name: 姓名
            phone: 电话
            department: 部门
            role: 角色

        Returns:
            更新后的用户对象

        Raises:
            NotFoundError: 用户不存在
        """
        user = await self.get_user_by_id(user_id, tenant_id=tenant_id)
        if not user:
            raise NotFoundError(resource_type="user", resource_id=str(user_id))

        if name is not None:
            user.name = name
        if phone is not None:
            user.phone = phone
        if department is not None:
            user.department = department
        if role is not None:
            user.role = role

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def set_user_status(
        self,
        user_id: UUID,
        status: UserStatus,
        reason: str | None = None,
        tenant_id: UUID | None = None,
        actor_id: UUID | None = None,
    ) -> User:
        """设置用户状态（启用/禁用）.

        Args:
            user_id: 用户ID
            status: 新状态
            reason: 操作原因

        Returns:
            更新后的用户对象

        Raises:
            NotFoundError: 用户不存在
            ForbiddenError: 不能禁用自己或超级管理员
        """
        user = await self.get_user_by_id(user_id, tenant_id=tenant_id)
        if not user:
            raise NotFoundError(resource_type="user", resource_id=str(user_id))
        if status == UserStatus.DISABLED and actor_id == user_id:
            raise ForbiddenError(message="不能禁用当前登录账号")
        if status == UserStatus.DISABLED and user.is_super_admin:
            raise ForbiddenError(message="不能禁用超级管理员")

        user.status = status
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def delete_user(
        self,
        user_id: UUID,
        deleted_by: UUID,
    ) -> None:
        """软删除用户.

        Args:
            user_id: 用户ID
            deleted_by: 删除操作人ID

        Raises:
            NotFoundError: 用户不存在
            ForbiddenError: 不能删除自己或超级管理员
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(resource_type="user", resource_id=str(user_id))

        # 软删除
        user.deleted_at = datetime.now(UTC)
        user.status = UserStatus.DISABLED

        await self.db.commit()

    async def get_user_stats(self, tenant_id: UUID) -> dict[str, int]:
        """获取用户统计信息.

        Args:
            tenant_id: 租户ID

        Returns:
            统计信息字典
        """
        stmt = select(
            func.count(User.id).label("total"),
            func.count(User.id).filter(User.status == UserStatus.ACTIVE).label("active"),
            func.count(User.id).filter(User.status == UserStatus.INVITED).label("invited"),
            func.count(User.id).filter(User.status == UserStatus.DISABLED).label("disabled"),
        ).where(
            User.tenant_id == tenant_id,
            User.deleted_at.is_(None),
        )

        result = await self.db.execute(stmt)
        row = result.one()

        return {
            "total": row.total or 0,
            "active": row.active or 0,
            "invited": row.invited or 0,
            "disabled": row.disabled or 0,
        }
