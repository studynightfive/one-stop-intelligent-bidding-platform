"""M5 资质库领域实体。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from app.domains.bids.ports import FileRefSnapshot, Role


@dataclass
class QualificationVersionEntity:
    id: str
    tenant_id: str
    qualification_id: str
    file: FileRefSnapshot
    document_version: str
    change_note: str
    created_by: str
    created_at: datetime


@dataclass(frozen=True)
class QualificationImportBindingEntity:
    job_id: str
    tenant_id: str
    category: str
    source_file_id: str
    actor_id: str
    actor_name: str
    actor_role: Role


@dataclass
class QualificationEntity:
    id: str
    tenant_id: str
    name: str
    category: str
    cert_number: str
    issuer: str
    file: FileRefSnapshot
    document_version: str
    reminder_days: list[int] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    valid_from: date | None = None
    expiry_date: date | None = None
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    deleted_reason: str | None = None


def qualification_status(entity: QualificationEntity, *, today: date | None = None) -> str:
    """根据有效期和提醒窗口动态计算状态，不持久化易过期的派生值。"""
    current = today or date.today()
    if entity.expiry_date is None:
        return "valid"
    days_left = (entity.expiry_date - current).days
    if days_left < 0:
        return "expired"
    expiring_window = max(entity.reminder_days, default=30)
    return "expiring" if days_left <= expiring_window else "valid"
