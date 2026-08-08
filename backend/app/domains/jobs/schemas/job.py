"""任务schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    """任务响应."""

    id: UUID = Field(..., description="任务ID")
    type: str = Field(..., description="任务类型")
    status: str = Field(..., description="状态: queued/running/succeeded/failed/cancelled")
    progress_percent: int = Field(..., description="进度百分比")
    current_step: str | None = Field(None, description="当前步骤")
    result: dict[str, Any] | None = Field(None, description="结果数据")
    error: dict[str, Any] | None = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")


class JobDetailResponse(BaseModel):
    """任务详情响应（包含更多字段）."""

    id: UUID = Field(..., description="任务ID")
    type: str = Field(..., description="任务类型")
    status: str = Field(..., description="状态: queued/running/succeeded/failed/cancelled")
    progress_percent: int = Field(..., description="进度百分比")
    current_step: str | None = Field(None, description="当前步骤")
    input_data: dict[str, Any] | None = Field(None, description="输入参数")
    result: dict[str, Any] | None = Field(None, description="结果数据")
    error: dict[str, Any] | None = Field(None, description="错误信息")
    project_id: UUID | None = Field(None, description="关联项目ID")
    started_at: datetime | None = Field(None, description="开始时间")
    completed_at: datetime | None = Field(None, description="完成时间")
    cancelled_at: datetime | None = Field(None, description="取消时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class JobCancelResponse(BaseModel):
    """取消任务响应."""

    id: UUID = Field(..., description="任务ID")
    status: str = Field(..., description="新状态")


class JobListResponse(BaseModel):
    """任务列表响应."""

    items: list[JobResponse] = Field(..., description="任务列表")
    total: int = Field(..., description="总数")
    limit: int = Field(..., description="每页数量")
    offset: int = Field(..., description="偏移量")


class RealtimeTicketRequest(BaseModel):
    """WebSocket票据请求."""

    channel: str = Field(..., description="通道类型: internal/portal")


class RealtimeTicketResponse(BaseModel):
    """WebSocket票据响应."""

    ticket: str = Field(..., description="一次性票据")
    expires_at: datetime = Field(..., description="过期时间")
