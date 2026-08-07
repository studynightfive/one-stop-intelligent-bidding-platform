"""通知schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    """通知响应."""
    id: UUID = Field(..., description="通知ID")
    type: str = Field(..., description="通知类型")
    title: str = Field(..., description="标题")
    content: str = Field(..., description="内容")
    is_read: bool = Field(..., description="是否已读")
    resource_type: str | None = Field(None, description="关联资源类型")
    resource_id: UUID | None = Field(None, description="关联资源ID")
    created_at: datetime = Field(..., description="创建时间")


class MarkReadRequest(BaseModel):
    """标记已读请求."""
    is_read: bool = Field(True, description="是否已读")


class NotificationListResponse(BaseModel):
    """通知列表响应."""
    notifications: list[NotificationResponse] = Field(..., description="通知列表")
    total: int = Field(..., description="总数")
    unread_count: int = Field(..., description="未读数量")


class MarkAllReadResponse(BaseModel):
    """全部已读响应."""
    updated_count: int = Field(..., description="更新数量")
