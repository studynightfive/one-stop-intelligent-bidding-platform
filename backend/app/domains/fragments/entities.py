"""片段库领域实体。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domains.bids.ports import FileRefSnapshot


@dataclass(slots=True)
class FragmentEntity:
    id: str
    tenant_id: str
    title: str
    category: str
    summary: str
    content: str
    tags: list[str]
    document_version: str
    source_file: FileRefSnapshot | None = None
    use_count: int = 0
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    deletion_reason: str | None = None


@dataclass(slots=True)
class FragmentVersionEntity:
    id: str
    tenant_id: str
    fragment_id: str
    version_number: int
    content: str
    document_version: str
    change_note: str
    created_by_id: str
    created_by_name: str
    source_file: FileRefSnapshot | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class FragmentReferenceEntity:
    id: str
    tenant_id: str
    fragment_id: str
    bid_task_id: str
    actor_id: str
    material_id: str | None = None
    created_at: datetime | None = None
