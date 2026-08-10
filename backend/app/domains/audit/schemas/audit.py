"""审计schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuditEventResponse(BaseModel):
    """审计事件响应."""

    id: UUID = Field(..., description="事件ID")
    tenant_id: UUID = Field(..., description="租户ID")
    aggregate_type: str = Field(..., description="聚合类型")
    aggregate_id: UUID = Field(..., description="聚合ID")
    actor_type: str = Field(..., description="操作者类型: user/supplier/system")
    actor_id: UUID | None = Field(None, description="操作者ID")
    actor_name: str = Field(..., description="操作者名称")
    action: str = Field(..., description="操作类型")
    target_type: str | None = Field(None, description="目标类型")
    target_id: UUID | None = Field(None, description="目标ID")
    summary: str = Field(..., description="摘要")
    changes: list[dict[str, Any]] | None = Field(None, description="变更内容")
    request_id: str = Field(..., description="请求ID")
    ip_address: str | None = Field(None, description="IP地址")
    created_at: datetime = Field(..., description="创建时间")


class AuditEventListResponse(BaseModel):
    """审计事件列表响应."""

    events: list[AuditEventResponse] = Field(..., description="事件列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")


class AuditEventExportResponse(BaseModel):
    """审计事件导出响应."""

    download_url: str = Field(..., description="导出文件下载URL")
