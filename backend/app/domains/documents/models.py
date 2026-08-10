"""Documents ORM 表（占位 L0 迁移使用）。

MIGRATION-NOTE（供 L0）:
- 新增表：bid_documents, bid_document_versions
- bid_documents:
  - id (UUIDv7, PK)
  - tenant_id (UUID, indexed)
  - task_id (UUID, FK -> bid_tasks.id)
  - type (varchar(32), 枚举 qualification|commercial|technical|merged)
  - current_version (int, default 0)
  - latest_file_id (UUID, nullable)
  - created_at / updated_at (timestamptz)
- bid_document_versions:
  - id (UUIDv7, PK)
  - tenant_id (UUID, indexed)
  - document_id (UUID, FK -> bid_documents.id)
  - version_number (int, 与 document_id 唯一)
  - file_id (UUID)
  - file_name (varchar(255))
  - mime_type (varchar(128))
  - size_bytes (bigint)
  - sha256 (varchar(64))
  - change_summary (text)
  - text_content (text, nullable；用于结构化版本比较，不保存二进制文件)
  - source_version_id (UUID, nullable, FK -> bid_document_versions.id)
  - roll_back (boolean, default false)
  - created_by_id (UUID)
  - created_by_name (varchar(128))
  - created_at (timestamptz)
- 索引：UNIQUE(document_id, version_number)；INDEX(tenant_id, task_id)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models_registry import Base


class BidDocumentModel(Base):
    __tablename__ = "bid_documents"
    __table_args__ = (Index("ix_bid_documents_tenant_task", "tenant_id", "task_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("bid_tasks.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latest_file_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    versions: Mapped[list[BidDocumentVersionModel]] = relationship(back_populates="document")


class BidDocumentVersionModel(Base):
    __tablename__ = "bid_document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_bid_document_version_number"),
        Index("ix_bid_document_versions_tenant_doc", "tenant_id", "document_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("bid_documents.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_id: Mapped[str] = mapped_column(String(36), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    text_content: Mapped[str | None] = mapped_column(Text)
    source_version_id: Mapped[str | None] = mapped_column(ForeignKey("bid_document_versions.id"))
    roll_back: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_by_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    document: Mapped[BidDocumentModel] = relationship(back_populates="versions")
