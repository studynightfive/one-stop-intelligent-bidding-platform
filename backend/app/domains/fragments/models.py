"""M5 fragments ORM 模型。

MIGRATION-NOTE（供 L0）:
- 新增 `fragments`、`fragment_versions`、`fragment_references`。
- `fragments` 使用 `(tenant_id, category)`、`(tenant_id, deleted_at)` 索引并保留软删除原因。
- `fragment_versions` 对 `(fragment_id, version_number)` 建唯一约束。
- `fragment_references` 保留投标任务、可选材料、操作者及时间，引用记录不物理删除。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models_registry import Base


class FragmentModel(Base):
    __tablename__ = "fragments"
    __table_args__ = (
        Index("ix_fragments_tenant_category", "tenant_id", "category"),
        Index("ix_fragments_tenant_deleted", "tenant_id", "deleted_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_file_id: Mapped[str | None] = mapped_column(String(128))
    source_file_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    document_version: Mapped[str] = mapped_column(String(128), nullable=False)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletion_reason: Mapped[str | None] = mapped_column(Text)


class FragmentVersionModel(Base):
    __tablename__ = "fragment_versions"
    __table_args__ = (
        UniqueConstraint("fragment_id", "version_number", name="uq_fragment_version_number"),
        Index("ix_fragment_versions_tenant_fragment", "tenant_id", "fragment_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    fragment_id: Mapped[str] = mapped_column(ForeignKey("fragments.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    document_version: Mapped[str] = mapped_column(String(128), nullable=False)
    change_note: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_id: Mapped[str | None] = mapped_column(String(128))
    source_file_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_by_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FragmentReferenceModel(Base):
    __tablename__ = "fragment_references"
    __table_args__ = (
        Index("ix_fragment_references_tenant_fragment", "tenant_id", "fragment_id"),
        Index("ix_fragment_references_tenant_bid", "tenant_id", "bid_task_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    fragment_id: Mapped[str] = mapped_column(ForeignKey("fragments.id"), nullable=False)
    bid_task_id: Mapped[str] = mapped_column(String(128), nullable=False)
    material_id: Mapped[str | None] = mapped_column(String(128))
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
