"""用户模型.

数据库表: users
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    pass


class UserRole(str, Enum):
    """用户角色枚举."""
    ADMIN = "admin"
    PROJECT_LEAD = "project_lead"
    MEMBER = "member"
    REVIEWER = "reviewer"


class UserStatus(str, Enum):
    """用户状态枚举."""
    INVITED = "invited"  # 已邀请待激活
    ACTIVE = "active"  # 活跃
    DISABLED = "disabled"  # 已禁用


class User(Base):
    """用户模型.

    属性:
        id: UUID主键
        tenant_id: 租户ID（多租户隔离）
        email: 邮箱（唯一）
        password_hash: 密码哈希
        name: 姓名
        phone: 电话号码
        role: 角色
        department: 部门
        status: 状态
        is_super_admin: 是否超级管理员
        last_login_at: 最后登录时间
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=False,  # 唯一性在 tenant_id + email 组合上
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=True,  # OAuth用户可能没有密码
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role"),
        default=UserRole.MEMBER,
        nullable=False,
    )
    department: Mapped[str] = mapped_column(
        String(100),
        default="",
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(UserStatus, name="user_status"),
        default=UserStatus.INVITED,
        nullable=False,
    )
    is_super_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # 索引
    __table_args__ = (
        Index("ix_users_tenant_email", "tenant_id", "email", unique=True),
        Index("ix_users_tenant_status", "tenant_id", "status"),
        Index("ix_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"

    def to_dict(self) -> dict:
        """转换为字典（不包含敏感字段）."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "email": self.email,
            "name": self.name,
            "phone": self.phone,
            "role": self.role.value,
            "department": self.department,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def is_active(self) -> bool:
        """用户是否活跃."""
        return self.status == UserStatus.ACTIVE

    @property
    def can_manage_users(self) -> bool:
        """是否可以管理用户."""
        return self.role == UserRole.ADMIN

    @property
    def can_create_projects(self) -> bool:
        """是否可以创建项目."""
        return self.role in (UserRole.ADMIN, UserRole.PROJECT_LEAD)

    @property
    def can_review(self) -> bool:
        """是否可以审核."""
        return self.role in (UserRole.ADMIN, UserRole.PROJECT_LEAD, UserRole.REVIEWER)
