"""通知服务.

提供通知的创建、查询、标记已读等操作。
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func as sql_func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.domains.notifications.models.notification import (
    Notification,
    NotificationType,
)


class NotificationService:
    """通知服务."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: UUID,
        tenant_id: UUID,
        notification_type: NotificationType,
        title: str,
        content: str,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> Notification:
        """创建通知.

        Args:
            user_id: 接收用户ID
            tenant_id: 租户ID
            notification_type: 通知类型
            title: 标题
            content: 内容
            resource_type: 关联资源类型
            resource_id: 关联资源ID
            extra_data: 额外元数据

        Returns:
            创建的通知对象
        """
        notification = Notification(
            user_id=user_id,
            tenant_id=tenant_id,
            type=notification_type,
            title=title,
            content=content,
            resource_type=resource_type,
            resource_id=resource_id,
            extra_data=extra_data,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def create_system_notification(
        self,
        user_id: UUID,
        tenant_id: UUID,
        title: str,
        content: str,
        **kwargs,
    ) -> Notification:
        """创建系统通知（快捷方法）."""
        return await self.create_notification(
            user_id=user_id,
            tenant_id=tenant_id,
            notification_type=NotificationType.SYSTEM,
            title=title,
            content=content,
            **kwargs,
        )

    async def create_task_notification(
        self,
        user_id: UUID,
        tenant_id: UUID,
        title: str,
        content: str,
        task_id: UUID,
        **kwargs,
    ) -> Notification:
        """创建任务通知（快捷方法）."""
        return await self.create_notification(
            user_id=user_id,
            tenant_id=tenant_id,
            notification_type=NotificationType.TASK,
            title=title,
            content=content,
            resource_type="task",
            resource_id=task_id,
            **kwargs,
        )

    async def create_review_notification(
        self,
        user_id: UUID,
        tenant_id: UUID,
        title: str,
        content: str,
        review_id: UUID,
        **kwargs,
    ) -> Notification:
        """创建评审通知（快捷方法）."""
        return await self.create_notification(
            user_id=user_id,
            tenant_id=tenant_id,
            notification_type=NotificationType.REVIEW,
            title=title,
            content=content,
            resource_type="review",
            resource_id=review_id,
            **kwargs,
        )

    async def get_notification_by_id(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification | None:
        """根据ID获取通知（带权限检查）.

        Args:
            notification_id: 通知ID
            user_id: 当前用户ID

        Returns:
            通知对象或None
        """
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,  # 只能查看自己的通知
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_notifications(
        self,
        user_id: UUID,
        tenant_id: UUID,
        notification_type: NotificationType | None = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Notification], int, int]:
        """查询通知列表.

        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            notification_type: 筛选类型
            unread_only: 仅未读
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            (通知列表, 总数, 未读数)
        """
        # 基础条件
        conditions = [
            Notification.user_id == user_id,
            Notification.tenant_id == tenant_id,
        ]

        if notification_type:
            conditions.append(Notification.type == notification_type)
        if unread_only:
            conditions.append(Notification.is_read == False)

        # 查询总数
        count_stmt = select(sql_func.count(Notification.id)).where(*conditions)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # 查询未读数
        unread_conditions = conditions + [Notification.is_read == False]
        unread_stmt = select(sql_func.count(Notification.id)).where(*unread_conditions)
        unread_result = await self.db.execute(unread_stmt)
        unread_count = unread_result.scalar_one()

        # 查询列表
        stmt = (
            select(Notification)
            .where(*conditions)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        notifications = list(result.scalars().all())

        return notifications, total, unread_count

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Notification:
        """标记通知为已读.

        Args:
            notification_id: 通知ID
            user_id: 当前用户ID

        Returns:
            更新后的通知对象

        Raises:
            NotFoundError: 通知不存在
        """
        notification = await self.get_notification_by_id(notification_id, user_id)
        if not notification:
            raise NotFoundError(message="通知不存在")

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(notification)

        return notification

    async def mark_as_unread(self, notification_id: UUID, user_id: UUID) -> Notification:
        """标记通知为未读.

        Args:
            notification_id: 通知ID
            user_id: 当前用户ID

        Returns:
            更新后的通知对象

        Raises:
            NotFoundError: 通知不存在
        """
        notification = await self.get_notification_by_id(notification_id, user_id)
        if not notification:
            raise NotFoundError(message="通知不存在")

        if notification.is_read:
            notification.is_read = False
            notification.read_at = None
            await self.db.commit()
            await self.db.refresh(notification)

        return notification

    async def mark_all_as_read(self, user_id: UUID, tenant_id: UUID) -> int:
        """将所有通知标记为已读.

        Args:
            user_id: 用户ID
            tenant_id: 租户ID

        Returns:
            更新数量
        """
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.tenant_id == tenant_id,
                Notification.is_read == False,
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def get_unread_count(self, user_id: UUID, tenant_id: UUID) -> int:
        """获取未读通知数量.

        Args:
            user_id: 用户ID
            tenant_id: 租户ID

        Returns:
            未读数量
        """
        stmt = select(sql_func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.tenant_id == tenant_id,
            Notification.is_read == False,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def delete_notification(self, notification_id: UUID, user_id: UUID) -> None:
        """删除通知（软删除）.

        Args:
            notification_id: 通知ID
            user_id: 当前用户ID

        Raises:
            NotFoundError: 通知不存在
        """
        notification = await self.get_notification_by_id(notification_id, user_id)
        if not notification:
            raise NotFoundError(message="通知不存在")

        # 软删除：标记为已读（也可以添加 deleted_at 字段）
        notification.is_read = True
        await self.db.commit()
