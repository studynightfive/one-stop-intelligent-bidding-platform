"""审计事件模型.

数据库表: audit_events
设计原则: append-only，不可修改或删除
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

if TYPE_CHECKING:
    pass


class ActorType(str, Enum):
    """操作者类型枚举."""
    USER = "user"  # 用户操作
    SUPPLIER = "supplier"  # 供应商操作
    SYSTEM = "system"  # 系统操作


class AuditEvent(Base):
    """审计事件模型.

    属性:
        id: UUID主键
        tenant_id: 租户ID（多租户隔离）
        aggregate_type: 聚合类型（如 project, bid, file）
        aggregate_id: 聚合ID
        actor_type: 操作者类型
        actor_id: 操作者ID
        actor_name: 操作者名称
        action: 操作类型（如 create, update, delete, approve, reject）
        target_type: 目标类型
        target_id: 目标ID
        summary: 摘要描述
        changes: 变更内容 (JSONB)
        request_id: 请求追踪ID
        ip_address: IP地址
        user_agent: User-Agent
        created_at: 创建时间（不可修改）
    """

    __tablename__ = "audit_events"

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
    aggregate_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    aggregate_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )
    actor_type: Mapped[ActorType] = mapped_column(
        String(20),
        default=ActorType.USER,
        nullable=False,
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    actor_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    target_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    target_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    changes: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    request_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 最大长度
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # 索引
    __table_args__ = (
        Index("ix_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_aggregate", "aggregate_type", "aggregate_id"),
        Index("ix_audit_actor", "actor_type", "actor_id"),
        Index("ix_audit_action", "action"),
    )

    def __repr__(self) -> str:
        return f"<AuditEvent {self.id} ({self.actor_name} {self.action})>"

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "aggregate_type": self.aggregate_type,
            "aggregate_id": str(self.aggregate_id),
            "actor_type": self.actor_type.value,
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "actor_name": self.actor_name,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": str(self.target_id) if self.target_id else None,
            "summary": self.summary,
            "changes": self.changes,
            "request_id": self.request_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
