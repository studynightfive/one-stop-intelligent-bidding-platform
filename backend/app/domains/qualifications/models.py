"""资质库 ORM 元数据。

MIGRATION-NOTE（供 L0 生成迁移，M5 不修改 ``migrations/versions``）：
- 新增 ``qualifications``：领域字段、file_id、version、软删除字段和审计时间；
  索引 ``(tenant_id, category)``、``(tenant_id, expiry_date)``、
  ``(tenant_id, deleted_at)``，``(tenant_id, cert_number)`` 唯一。
- 新增 ``qualification_versions``：资质/文件/文档版本/change_note/创建人/时间；
  索引 ``(tenant_id, qualification_id, created_at)``。
- 新增 ``qualification_import_jobs``：以 ``(tenant_id, file_id)`` 唯一约束保证导入幂等，
  ``(tenant_id, job_id)`` 唯一约束保证终态互斥；保存 category、原始操作者、
  成功结果或失败消息及完成时间。
- upgrade：创建上述三表和索引；既有数据无需回填。
- downgrade：仅在确认无业务数据时按 import_jobs -> versions -> qualifications 顺序删除。
- 数据风险：cert_number 的租户内唯一约束可能拒绝历史重复证书号，迁移前需由 L0 检查。
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models_registry import Base


class QualificationModel(Base):
    __tablename__ = "qualifications"
    __table_args__ = (
        UniqueConstraint("tenant_id", "cert_number", name="uq_qualifications_tenant_cert"),
        Index("ix_qualifications_tenant_category", "tenant_id", "category"),
        Index("ix_qualifications_tenant_expiry", "tenant_id", "expiry_date"),
        Index("ix_qualifications_tenant_deleted", "tenant_id", "deleted_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    cert_number: Mapped[str] = mapped_column(String(128), nullable=False)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    file_id: Mapped[str] = mapped_column(String(36), nullable=False)
    document_version: Mapped[str] = mapped_column(String(64), nullable=False)
    reminder_days: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[str | None] = mapped_column(String(36))
    deleted_reason: Mapped[str | None] = mapped_column(Text)


class QualificationVersionModel(Base):
    __tablename__ = "qualification_versions"
    __table_args__ = (
        Index(
            "ix_qualification_versions_tenant_qualification",
            "tenant_id",
            "qualification_id",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    qualification_id: Mapped[str] = mapped_column(ForeignKey("qualifications.id"), nullable=False)
    file_id: Mapped[str] = mapped_column(String(36), nullable=False)
    document_version: Mapped[str] = mapped_column(String(64), nullable=False)
    change_note: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QualificationImportJobModel(Base):
    __tablename__ = "qualification_import_jobs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "file_id", name="uq_qualification_import_tenant_file"),
        UniqueConstraint("tenant_id", "job_id", name="uq_qualification_import_tenant_job"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    actor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    result_payload: Mapped[dict[str, object] | list[dict[str, object]] | None] = mapped_column(JSON)
    failure_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
