"""通知模型.

数据库表: notifications
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

if TYPE_CHECKING:
    pass


class NotificationType(str, Enum):
    """通知类型枚举."""

    SYSTEM = "system"  # 系统通知
    TASK = "task"  # 任务通知
    REVIEW = "review"  # 评审通知
    APPROVAL = "approval"  # 审批通知
    MESSAGE = "message"  # 消息通知
    ASSIGNMENT = "assignment"  # 分配通知


class Notification(Base):
    """通知模型.

    属性:
        id: UUID主键
        tenant_id: 租户ID（多租户隔离）
        user_id: 接收用户ID
        type: 通知类型
        title: 标题
        content: 内容
        is_read: 是否已读
        resource_type: 关联资源类型
        resource_id: 关联资源ID
        metadata: 额外元数据 (JSONB)
        created_at: 创建时间
        read_at: 阅读时间
    """

    __tablename__ = "notifications"

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
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )
    type: Mapped[NotificationType] = mapped_column(
        SQLEnum(NotificationType, name="notification_type"),
        default=NotificationType.SYSTEM,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    resource_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    resource_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # 索引
    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("ix_notifications_tenant_created", "tenant_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Notification {self.id} ({self.type.value})>"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "user_id": str(self.user_id),
            "type": self.type.value,
            "title": self.title,
            "content": self.content,
            "is_read": self.is_read,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }
