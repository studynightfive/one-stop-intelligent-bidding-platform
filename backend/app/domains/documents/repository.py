"""Documents 仓储（内存实现）。"""

from __future__ import annotations

import copy
from typing import Any

from app.domains.documents.entities import (
    DocumentEntity,
    DocumentVersionEntity,
)
from app.domains.documents.errors import not_found


class DocumentStore:
    def __init__(self) -> None:
        self.documents: dict[str, DocumentEntity] = {}
        self.versions: dict[str, DocumentVersionEntity] = {}

    # ---- Document CRUD ----
    def save_document(self, entity: DocumentEntity) -> DocumentEntity:
        self.documents[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def get_document(self, document_id: str, *, tenant_id: str) -> DocumentEntity:
        doc = self.documents.get(document_id)
        if doc is None or doc.tenant_id != tenant_id:
            raise not_found("文档不存在", documentId=document_id)
        # 装填版本列表（按 version_number 升序）
        doc.versions = sorted(
            (v for v in self.versions.values() if v.document_id == document_id and v.tenant_id == tenant_id),
            key=lambda v: v.version_number,
        )
        return copy.deepcopy(doc)

    def list_documents_by_task(self, *, tenant_id: str, task_id: str) -> list[DocumentEntity]:
        items = [copy.deepcopy(d) for d in self.documents.values() if d.tenant_id == tenant_id and d.task_id == task_id]
        for item in items:
            item.versions = sorted(
                (v for v in self.versions.values() if v.document_id == item.id and v.tenant_id == tenant_id),
                key=lambda v: v.version_number,
            )
        return items

    def find_document_by_type(self, *, tenant_id: str, task_id: str, doc_type: str) -> DocumentEntity | None:
        for doc in self.documents.values():
            if doc.tenant_id == tenant_id and doc.task_id == task_id and doc.doc_type == doc_type:
                return copy.deepcopy(doc)
        return None

    # ---- Version CRUD ----
    def save_version(self, entity: DocumentVersionEntity) -> DocumentVersionEntity:
        document = self.documents.get(entity.document_id)
        if document is None or document.tenant_id != entity.tenant_id:
            raise not_found("文档不存在", documentId=entity.document_id)
        self.versions[entity.id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    def get_version(self, version_id: str, *, tenant_id: str) -> DocumentVersionEntity:
        version = self.versions.get(version_id)
        if version is None or version.tenant_id != tenant_id:
            raise not_found("文档版本不存在", versionId=version_id)
        return copy.deepcopy(version)

    def get_versions_for_document(self, *, document_id: str) -> list[DocumentVersionEntity]:
        items = [v for v in self.versions.values() if v.document_id == document_id]
        items.sort(key=lambda v: v.version_number, reverse=True)
        return [copy.deepcopy(v) for v in items]

    def list_versions_by_task(self, *, tenant_id: str, task_id: str) -> list[DocumentVersionEntity]:
        doc_ids = {d.id for d in self.documents.values() if d.tenant_id == tenant_id and d.task_id == task_id}
        items = [v for v in self.versions.values() if v.document_id in doc_ids]
        items.sort(key=lambda v: v.created_at, reverse=True)
        return [copy.deepcopy(v) for v in items]

    def latest_version(self, document_id: str) -> DocumentVersionEntity | None:
        items = [v for v in self.versions.values() if v.document_id == document_id]
        if not items:
            return None
        items.sort(key=lambda v: v.version_number, reverse=True)
        return copy.deepcopy(items[0])

    def next_version_number(self, document_id: str) -> int:
        items = [v for v in self.versions.values() if v.document_id == document_id]
        if not items:
            return 1
        return max(v.version_number for v in items) + 1


def default_repository() -> DocumentStore:
    return DocumentStore()


def document_from_orm_row(row: Any) -> DocumentEntity:
    """供 M0 持久化阶段使用：把 ORM 行映射为实体。"""
    return DocumentEntity(
        id=str(row.id),
        task_id=str(row.task_id),
        tenant_id=str(row.tenant_id),
        doc_type=str(row.type),
        current_version=int(row.current_version or 0),
        latest_file_id=str(row.latest_file_id) if row.latest_file_id else None,
        created_at=getattr(row, "created_at", None),
        updated_at=getattr(row, "updated_at", None),
    )
