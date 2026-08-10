"""Notification 模型和服务测试."""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications.models.notification import (
    Notification,
    NotificationType,
)
from app.domains.notifications.services.notification_service import (
    NotificationService,
)


class TestNotificationModel:
    """Notification 模型测试."""

    def test_notification_type_enum_values(self) -> None:
        """测试 NotificationType 枚举值."""
        assert NotificationType.SYSTEM.value == "system"
        assert NotificationType.TASK.value == "task"
        assert NotificationType.REVIEW.value == "review"
        assert NotificationType.APPROVAL.value == "approval"
        assert NotificationType.MESSAGE.value == "message"
        assert NotificationType.ASSIGNMENT.value == "assignment"

    def test_notification_to_dict(self) -> None:
        """测试 to_dict 方法."""
        notification_id = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()

        notification = Notification(
            id=notification_id,
            tenant_id=tenant_id,
            user_id=user_id,
            type=NotificationType.SYSTEM,
            title="系统通知",
            content="这是一个测试通知",
            is_read=False,
        )

        result = notification.to_dict()

        assert result["id"] == str(notification_id)
        assert result["tenant_id"] == str(tenant_id)
        assert result["user_id"] == str(user_id)
        assert result["type"] == "system"
        assert result["title"] == "系统通知"
        assert result["content"] == "这是一个测试通知"
        assert result["is_read"] is False
        assert result["extra_data"] is None


class TestNotificationService:
    """NotificationService 测试."""

    @pytest_asyncio.fixture
    async def notification_service(
        self,
        db_session: AsyncSession,
    ) -> NotificationService:
        """创建 NotificationService 实例."""
        return NotificationService(db_session)

    @pytest.mark.asyncio
    async def test_create_notification(
        self,
        notification_service: NotificationService,
    ) -> None:
        """测试创建通知."""
        user_id = uuid4()
        tenant_id = uuid4()

        notification = await notification_service.create_notification(
            user_id=user_id,
            tenant_id=tenant_id,
            notification_type=NotificationType.SYSTEM,
            title="测试通知",
            content="这是测试通知的内容",
        )

        assert notification.id is not None
        assert notification.user_id == user_id
        assert notification.tenant_id == tenant_id
        assert notification.type == NotificationType.SYSTEM
        assert notification.title == "测试通知"
        assert notification.is_read is False

    @pytest.mark.asyncio
    async def test_create_system_notification(
        self,
        notification_service: NotificationService,
    ) -> None:
        """测试创建系统通知快捷方法."""
        user_id = uuid4()
        tenant_id = uuid4()

        notification = await notification_service.create_system_notification(
            user_id=user_id,
            tenant_id=tenant_id,
            title="系统消息",
            content="系统维护通知",
        )

        assert notification.type == NotificationType.SYSTEM
        assert notification.title == "系统消息"

    @pytest.mark.asyncio
    async def test_create_task_notification(
        self,
        notification_service: NotificationService,
    ) -> None:
        """测试创建任务通知快捷方法."""
        user_id = uuid4()
        tenant_id = uuid4()
        task_id = uuid4()

        notification = await notification_service.create_task_notification(
            user_id=user_id,
            tenant_id=tenant_id,
            title="任务完成",
            content="文件扫描任务已完成",
            task_id=task_id,
        )

        assert notification.type == NotificationType.TASK
        assert notification.resource_type == "task"
        assert notification.resource_id == task_id

    @pytest.mark.asyncio
    async def test_list_notifications(
        self,
        notification_service: NotificationService,
    ) -> None:
        """测试查询通知列表."""
        user_id = uuid4()
        tenant_id = uuid4()

        # 创建多条通知
        for i in range(3):
            await notification_service.create_notification(
                user_id=user_id,
                tenant_id=tenant_id,
                notification_type=NotificationType.SYSTEM,
                title=f"通知 {i}",
                content=f"内容 {i}",
            )

        notifications, total, unread_count = await notification_service.list_notifications(
            user_id=user_id,
            tenant_id=tenant_id,
        )

        assert total == 3
        assert unread_count == 3
        assert len(notifications) == 3

    @pytest.mark.asyncio
    async def test_mark_as_read(
        self,
        notification_service: NotificationService,
    ) -> None:
        """测试标记已读."""
        user_id = uuid4()
        tenant_id = uuid4()

        notification = await notification_service.create_notification(
            user_id=user_id,
            tenant_id=tenant_id,
            notification_type=NotificationType.SYSTEM,
            title="测试",
            content="测试内容",
        )

        assert notification.is_read is False

        updated = await notification_service.mark_as_read(
            notification_id=notification.id,
            user_id=user_id,
        )

        assert updated.is_read is True
        assert updated.read_at is not None

    @pytest.mark.asyncio
    async def test_mark_all_as_read(
        self,
        notification_service: NotificationService,
    ) -> None:
        """测试全部标记已读."""
        user_id = uuid4()
        tenant_id = uuid4()

        # 创建多条通知
        for i in range(5):
            await notification_service.create_notification(
                user_id=user_id,
                tenant_id=tenant_id,
                notification_type=NotificationType.SYSTEM,
                title=f"通知 {i}",
                content=f"内容 {i}",
            )

        updated_count = await notification_service.mark_all_as_read(
            user_id=user_id,
            tenant_id=tenant_id,
        )

        assert updated_count == 5

        # 验证未读数为0
        unread_count = await notification_service.get_unread_count(
            user_id=user_id,
            tenant_id=tenant_id,
        )
        assert unread_count == 0

    @pytest.mark.asyncio
    async def test_get_unread_count(
        self,
        notification_service: NotificationService,
    ) -> None:
        """测试获取未读数量."""
        user_id = uuid4()
        tenant_id = uuid4()

        # 创建通知
        for i in range(3):
            await notification_service.create_notification(
                user_id=user_id,
                tenant_id=tenant_id,
                notification_type=NotificationType.SYSTEM,
                title=f"通知 {i}",
                content=f"内容 {i}",
            )

        unread_count = await notification_service.get_unread_count(
            user_id=user_id,
            tenant_id=tenant_id,
        )

        assert unread_count == 3

    @pytest.mark.asyncio
    async def test_notification_not_found(
        self,
        notification_service: NotificationService,
    ) -> None:
        """测试查询不存在的通知."""
        from app.core.errors import NotFoundError

        with pytest.raises(NotFoundError):
            await notification_service.mark_as_read(
                notification_id=uuid4(),
                user_id=uuid4(),
            )
