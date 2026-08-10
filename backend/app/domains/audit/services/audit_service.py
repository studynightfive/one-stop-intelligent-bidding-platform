"""审计服务.

提供审计事件的记录和查询功能。
设计原则: append-only，不可修改或删除。
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func as sql_func
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.models.audit_event import ActorType, AuditEvent


class AuditService:
    """审计服务.

    使用示例:
        audit_service = AuditService(db)

        # 记录审计事件
        await audit_service.log(
            tenant_id=tenant_id,
            aggregate_type="project",
            aggregate_id=project_id,
            actor_id=user_id,
            actor_name=user_name,
            action="create",
            summary=f"创建项目: {project_name}",
        )

        # 查询审计事件
        events, total = await audit_service.list_events(
            tenant_id=tenant_id,
            aggregate_type="project",
            aggregate_id=project_id,
        )
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        tenant_id: UUID,
        aggregate_type: str,
        aggregate_id: UUID,
        action: str,
        summary: str,
        actor_type: ActorType = ActorType.USER,
        actor_id: UUID | None = None,
        actor_name: str = "System",
        target_type: str | None = None,
        target_id: UUID | None = None,
        changes: dict[str, Any] | None = None,
        request_id: str = "",
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditEvent:
        """记录审计事件.

        Args:
            tenant_id: 租户ID
            aggregate_type: 聚合类型（如 project, bid, file）
            aggregate_id: 聚合ID
            action: 操作类型（如 create, update, delete）
            summary: 摘要描述
            actor_type: 操作者类型
            actor_id: 操作者ID
            actor_name: 操作者名称
            target_type: 目标类型
            target_id: 目标ID
            changes: 变更内容
            request_id: 请求追踪ID
            ip_address: IP地址
            user_agent: User-Agent

        Returns:
            创建的审计事件对象
        """
        event = AuditEvent(
            tenant_id=tenant_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_name=actor_name,
            action=action,
            target_type=target_type,
            target_id=target_id,
            summary=summary,
            changes=changes,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def log_user_action(
        self,
        tenant_id: UUID,
        user_id: UUID,
        user_name: str,
        aggregate_type: str,
        aggregate_id: UUID,
        action: str,
        summary: str,
        **kwargs: Any,
    ) -> AuditEvent:
        """记录用户操作（快捷方法）.

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            user_name: 用户名
            aggregate_type: 聚合类型
            aggregate_id: 聚合ID
            action: 操作类型
            summary: 摘要
            **kwargs: 其他参数传递给 log()

        Returns:
            创建的审计事件对象
        """
        return await self.log(
            tenant_id=tenant_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            actor_type=ActorType.USER,
            actor_id=user_id,
            actor_name=user_name,
            action=action,
            summary=summary,
            **kwargs,
        )

    async def log_system_action(
        self,
        tenant_id: UUID,
        aggregate_type: str,
        aggregate_id: UUID,
        action: str,
        summary: str,
        **kwargs: Any,
    ) -> AuditEvent:
        """记录系统操作（快捷方法）.

        Args:
            tenant_id: 租户ID
            aggregate_type: 聚合类型
            aggregate_id: 聚合ID
            action: 操作类型
            summary: 摘要
            **kwargs: 其他参数传递给 log()

        Returns:
            创建的审计事件对象
        """
        return await self.log(
            tenant_id=tenant_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            actor_name="System",
            action=action,
            summary=summary,
            **kwargs,
        )

    async def list_events(
        self,
        tenant_id: UUID,
        aggregate_type: str | None = None,
        aggregate_id: UUID | None = None,
        actor_id: UUID | None = None,
        actor_name: str | None = None,
        action: str | None = None,
        resource: str | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditEvent], int]:
        """查询审计事件列表.

        Args:
            tenant_id: 租户ID
            aggregate_type: 聚合类型筛选
            aggregate_id: 聚合ID筛选
            actor_id: 操作者ID筛选
            actor_name: 操作者名称模糊筛选
            action: 操作类型筛选
            resource: 聚合或目标资源类型筛选
            target_type: 目标类型筛选
            target_id: 目标ID筛选
            start_date: 开始时间
            end_date: 结束时间
            sort_order: 创建时间排序方向
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            (审计事件列表, 总数)
        """
        # 基础条件
        conditions = [AuditEvent.tenant_id == tenant_id]

        if aggregate_type:
            conditions.append(AuditEvent.aggregate_type == aggregate_type)
        if aggregate_id:
            conditions.append(AuditEvent.aggregate_id == aggregate_id)
        if actor_id:
            conditions.append(AuditEvent.actor_id == actor_id)
        if actor_name:
            conditions.append(AuditEvent.actor_name.ilike(f"%{actor_name}%"))
        if action:
            conditions.append(AuditEvent.action == action)
        if resource:
            conditions.append(or_(AuditEvent.aggregate_type == resource, AuditEvent.target_type == resource))
        if target_type:
            conditions.append(AuditEvent.target_type == target_type)
        if target_id:
            conditions.append(AuditEvent.target_id == target_id)
        if start_date:
            conditions.append(AuditEvent.created_at >= start_date)
        if end_date:
            conditions.append(AuditEvent.created_at <= end_date)

        # 查询总数
        count_stmt = select(sql_func.count(AuditEvent.id)).where(*conditions)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # 查询列表
        created_at_order = AuditEvent.created_at.asc() if sort_order == "asc" else AuditEvent.created_at.desc()
        stmt = select(AuditEvent).where(*conditions).order_by(created_at_order).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        events = list(result.scalars().all())

        return events, total

    async def get_event_by_id(
        self,
        event_id: UUID,
        tenant_id: UUID,
    ) -> AuditEvent | None:
        """根据ID获取审计事件.

        Args:
            event_id: 事件ID
            tenant_id: 租户ID（用于权限检查）

        Returns:
            审计事件对象或None
        """
        stmt = select(AuditEvent).where(
            AuditEvent.id == event_id,
            AuditEvent.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_resource_history(
        self,
        tenant_id: UUID,
        aggregate_type: str,
        aggregate_id: UUID,
        limit: int = 50,
    ) -> list[AuditEvent]:
        """获取资源的操作历史.

        Args:
            tenant_id: 租户ID
            aggregate_type: 聚合类型
            aggregate_id: 聚合ID
            limit: 返回数量限制

        Returns:
            审计事件列表
        """
        events, _ = await self.list_events(
            tenant_id=tenant_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            limit=limit,
        )
        return events

    async def get_user_activity(
        self,
        tenant_id: UUID,
        user_id: UUID,
        limit: int = 50,
    ) -> list[AuditEvent]:
        """获取用户的操作活动.

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            limit: 返回数量限制

        Returns:
            审计事件列表
        """
        events, _ = await self.list_events(
            tenant_id=tenant_id,
            actor_id=user_id,
            limit=limit,
        )
        return events
