"""文件上传会话模型.

数据库表: file_upload_sessions
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    pass


class UploadStatus(str, Enum):
    """上传状态枚举."""
    CREATED = "created"
    UPLOADING = "uploading"
    VERIFYING = "verifying"
    SCANNING = "scanning"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ScanStatus(str, Enum):
    """扫描状态枚举."""
    PENDING = "pending"
    CLEAN = "clean"
    INFECTED = "infected"
    FAILED = "failed"


class FileUploadSession(Base):
    """文件上传会话模型.

    用于支持大文件分片上传。
    """

    __tablename__ = "file_upload_sessions"

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
        index=True,
    )

    # 文件信息
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=True)

    # 分片信息
    part_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_parts: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_parts: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # 状态
    status: Mapped[UploadStatus] = mapped_column(
        SQLEnum(UploadStatus, name="upload_status"),
        default=UploadStatus.CREATED,
        nullable=False,
    )
    scan_status: Mapped[ScanStatus] = mapped_column(
        SQLEnum(ScanStatus, name="scan_status"),
        default=ScanStatus.PENDING,
        nullable=False,
    )

    # 上传目的
    purpose: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
    )
    resource_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    # 存储信息
    minio_object_key: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # 过期时间
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # 时间戳
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

    __table_args__ = (
        Index("ix_sessions_user_status", "user_id", "status"),
        Index("ix_sessions_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<FileUploadSession {self.file_name} ({self.status.value})>"

    @property
    def is_expired(self) -> bool:
        """会话是否已过期."""
        return datetime.now(self.expires_at.tzinfo) > self.expires_at

    @property
    def is_completed(self) -> bool:
        """上传是否完成."""
        return self.status == UploadStatus.COMPLETED

    @property
    def uploaded_count(self) -> int:
        """已上传分片数."""
        return len(self.uploaded_parts)


class File(Base):
    """文件元数据模型.

    记录已上传文件的基本信息。
    """

    __tablename__ = "files"

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
    uploader_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # 文件基本信息
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # 存储信息
    minio_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    minio_object_key: Mapped[str] = mapped_column(String(500), nullable=False)

    # 扫描状态
    scan_status: Mapped[ScanStatus] = mapped_column(
        SQLEnum(ScanStatus, name="scan_status"),
        default=ScanStatus.PENDING,
        nullable=False,
    )

    # 使用目的
    purpose: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
    )
    resource_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    resource_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_files_tenant_purpose", "tenant_id", "purpose"),
        Index("ix_files_resource", "resource_type", "resource_id"),
    )

    def __repr__(self) -> str:
        return f"<File {self.file_name}>"
