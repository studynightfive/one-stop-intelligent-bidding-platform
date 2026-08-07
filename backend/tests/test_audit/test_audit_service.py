"""AuditEvent 模型和服务测试."""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.models.audit_event import ActorType, AuditEvent
from app.domains.audit.services.audit_service import AuditService


class TestAuditEventModel:
    """AuditEvent 模型测试."""

    def test_actor_type_enum_values(self) -> None:
        """测试 ActorType 枚举值."""
        assert ActorType.USER.value == "user"
        assert ActorType.SUPPLIER.value == "supplier"
        assert ActorType.SYSTEM.value == "system"

    def test_audit_event_to_dict(self) -> None:
        """测试 to_dict 方法."""
        event_id = uuid4()
        tenant_id = uuid4()
        aggregate_id = uuid4()
        actor_id = uuid4()

        event = AuditEvent(
            id=event_id,
            tenant_id=tenant_id,
            aggregate_type="project",
            aggregate_id=aggregate_id,
            actor_type=ActorType.USER,
            actor_id=actor_id,
            actor_name="Test User",
            action="create",
            summary="创建项目测试",
            request_id="req-123",
            ip_address="192.168.1.1",
        )

        result = event.to_dict()

        assert result["id"] == str(event_id)
        assert result["tenant_id"] == str(tenant_id)
        assert result["aggregate_type"] == "project"
        assert result["aggregate_id"] == str(aggregate_id)
        assert result["actor_type"] == "user"
        assert result["actor_id"] == str(actor_id)
        assert result["actor_name"] == "Test User"
        assert result["action"] == "create"
        assert result["summary"] == "创建项目测试"
        assert result["request_id"] == "req-123"
        assert result["ip_address"] == "192.168.1.1"


class TestAuditService:
    """AuditService 测试."""

    @pytest_asyncio.fixture
    async def audit_service(self, db_session: AsyncSession) -> AuditService:
        """创建 AuditService 实例."""
        return AuditService(db_session)

    @pytest.mark.asyncio
    async def test_log_audit_event(self, audit_service: AuditService) -> None:
        """测试记录审计事件."""
        tenant_id = uuid4()
        aggregate_id = uuid4()
        actor_id = uuid4()

        event = await audit_service.log(
            tenant_id=tenant_id,
            aggregate_type="project",
            aggregate_id=aggregate_id,
            actor_type=ActorType.USER,
            actor_id=actor_id,
            actor_name="Test User",
            action="create",
            summary="创建新项目",
            request_id="req-456",
            ip_address="10.0.0.1",
        )

        assert event.id is not None
        assert event.tenant_id == tenant_id
        assert event.aggregate_type == "project"
        assert event.aggregate_id == aggregate_id
        assert event.actor_type == ActorType.USER
        assert event.actor_id == actor_id
        assert event.action == "create"
        assert event.summary == "创建新项目"

    @pytest.mark.asyncio
    async def test_log_user_action(self, audit_service: AuditService) -> None:
        """测试记录用户操作快捷方法."""
        tenant_id = uuid4()
        user_id = uuid4()
        aggregate_id = uuid4()

        event = await audit_service.log_user_action(
            tenant_id=tenant_id,
            user_id=user_id,
            user_name="张三",
            aggregate_type="bid",
            aggregate_id=aggregate_id,
            action="submit",
            summary="提交投标文件",
        )

        assert event.actor_type == ActorType.USER
        assert event.actor_id == user_id
        assert event.actor_name == "张三"
        assert event.action == "submit"

    @pytest.mark.asyncio
    async def test_log_system_action(self, audit_service: AuditService) -> None:
        """测试记录系统操作快捷方法."""
        tenant_id = uuid4()
        aggregate_id = uuid4()

        event = await audit_service.log_system_action(
            tenant_id=tenant_id,
            aggregate_type="job",
            aggregate_id=aggregate_id,
            action="complete",
            summary="自动任务完成",
        )

        assert event.actor_type == ActorType.SYSTEM
        assert event.actor_name == "System"
        assert event.action == "complete"

    @pytest.mark.asyncio
    async def test_list_events(self, audit_service: AuditService) -> None:
        """测试查询审计事件列表."""
        tenant_id = uuid4()
        aggregate_id = uuid4()

        # 创建多条审计事件
        for i in range(3):
            await audit_service.log(
                tenant_id=tenant_id,
                aggregate_type="project",
                aggregate_id=aggregate_id,
                action="update",
                summary=f"更新 {i}",
                actor_name="Test",
            )

        events, total = await audit_service.list_events(
            tenant_id=tenant_id,
            aggregate_type="project",
            aggregate_id=aggregate_id,
        )

        assert total == 3
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_list_events_with_filter(
        self,
        audit_service: AuditService,
    ) -> None:
        """测试带筛选条件的审计事件列表."""
        tenant_id = uuid4()
        aggregate_id = uuid4()
        user_id = uuid4()

        # 创建不同操作类型的事件
        await audit_service.log_user_action(
            tenant_id=tenant_id,
            user_id=user_id,
            user_name="User1",
            aggregate_type="project",
            aggregate_id=aggregate_id,
            action="create",
            summary="创建",
        )
        await audit_service.log_user_action(
            tenant_id=tenant_id,
            user_id=user_id,
            user_name="User1",
            aggregate_type="project",
            aggregate_id=aggregate_id,
            action="update",
            summary="更新",
        )

        # 按操作类型筛选
        events, total = await audit_service.list_events(
            tenant_id=tenant_id,
            action="create",
        )

        assert total == 1
        assert events[0].action == "create"

    @pytest.mark.asyncio
    async def test_get_resource_history(
        self,
        audit_service: AuditService,
    ) -> None:
        """测试获取资源操作历史."""
        tenant_id = uuid4()
        aggregate_id = uuid4()

        # 创建多个事件
        for action in ["create", "update", "update", "delete"]:
            await audit_service.log(
                tenant_id=tenant_id,
                aggregate_type="document",
                aggregate_id=aggregate_id,
                action=action,
                summary=f"文档操作: {action}",
                actor_name="Test User",
            )

        history = await audit_service.get_resource_history(
            tenant_id=tenant_id,
            aggregate_type="document",
            aggregate_id=aggregate_id,
        )

        assert len(history) == 4

    @pytest.mark.asyncio
    async def test_get_user_activity(
        self,
        audit_service: AuditService,
    ) -> None:
        """测试获取用户操作活动."""
        tenant_id = uuid4()
        user_id = uuid4()

        # 创建多个事件
        for i in range(5):
            await audit_service.log_user_action(
                tenant_id=tenant_id,
                user_id=user_id,
                user_name="Activity User",
                aggregate_type="project",
                aggregate_id=uuid4(),
                action="update",
                summary=f"更新项目 {i}",
            )

        activities = await audit_service.get_user_activity(
            tenant_id=tenant_id,
            user_id=user_id,
        )

        assert len(activities) == 5
        assert all(a.actor_id == user_id for a in activities)

    @pytest.mark.asyncio
    async def test_audit_event_with_changes(
        self,
        audit_service: AuditService,
    ) -> None:
        """测试带变更记录的审计事件."""
        tenant_id = uuid4()
        aggregate_id = uuid4()

        changes = {
            "before": {"status": "draft"},
            "after": {"status": "published"},
        }

        event = await audit_service.log(
            tenant_id=tenant_id,
            aggregate_type="project",
            aggregate_id=aggregate_id,
            action="update",
            summary="更新项目状态",
            changes=changes,
            actor_name="Admin",
        )

        assert event.changes == changes
