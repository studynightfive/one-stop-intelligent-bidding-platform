"""任务模型.

数据库表: jobs
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

if TYPE_CHECKING:
    pass


class JobStatus(str, Enum):
    """任务状态枚举."""

    QUEUED = "queued"  # 排队中
    RUNNING = "running"  # 执行中
    SUCCEEDED = "succeeded"  # 成功
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class JobType(str, Enum):
    """任务类型枚举."""

    FILE_SCAN = "file_scan"  # 文件扫描
    FILE_IMPORT = "file_import"  # 文件导入
    DOCUMENT_GENERATION = "document_generation"  # 文档生成
    AI_ANALYSIS = "ai_analysis"  # AI分析
    EXPORT = "export"  # 导出
    OTHER = "other"  # 其他


class Job(Base):
    """异步任务模型.

    属性:
        id: UUID主键
        tenant_id: 租户ID（多租户隔离）
        user_id: 创建者ID
        project_id: 关联项目ID（可选）
        type: 任务类型
        status: 任务状态
        progress_percent: 进度百分比 (0-100)
        current_step: 当前步骤描述
        input_data: 输入参数 (JSONB)
        result: 结果数据 (JSONB)
        error: 错误信息 (JSONB)
        celery_task_id: Celery任务ID
        started_at: 开始时间
        completed_at: 完成时间
        cancelled_at: 取消时间
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = "jobs"

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
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    type: Mapped[JobType] = mapped_column(
        SQLEnum(JobType, name="job_type"),
        default=JobType.OTHER,
        nullable=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, name="job_status"),
        default=JobStatus.QUEUED,
        nullable=False,
        index=True,
    )
    progress_percent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    current_step: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    input_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    error: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    is_cancelled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
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

    # 索引
    __table_args__ = (
        Index("ix_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_jobs_user_status", "user_id", "status"),
        Index("ix_jobs_tenant_created", "tenant_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Job {self.id} ({self.type.value}/{self.status.value})>"

    @property
    def is_finished(self) -> bool:
        """任务是否已结束（成功/失败/取消）."""
        return self.status in (
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        )

    @property
    def is_cancellable(self) -> bool:
        """任务是否可取消."""
        return self.status in (JobStatus.QUEUED, JobStatus.RUNNING) and not self.is_cancelled

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "user_id": str(self.user_id),
            "project_id": str(self.project_id) if self.project_id else None,
            "type": self.type.value,
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "input_data": self.input_data,
            "result": self.result,
            "error": self.error,
            "celery_task_id": self.celery_task_id,
            "is_cancelled": self.is_cancelled,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
