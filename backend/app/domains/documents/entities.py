"""Documents 域实体：Document、DocumentVersion、DocumentChange。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DocumentEntity:
    """聚合根：一次生成的 Word 文档。"""

    id: str
    task_id: str
    tenant_id: str
    doc_type: str  # qualification | commercial | technical | merged
    current_version: int = 0
    latest_file_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    versions: list[DocumentVersionEntity] = field(default_factory=list)


@dataclass
class DocumentVersionEntity:
    """DocumentVersion：单次生成/回滚产生的版本。"""

    id: str
    document_id: str
    tenant_id: str
    version_number: int
    file_id: str
    file_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    change_summary: str
    created_by_id: str
    created_by_name: str
    created_at: datetime
    source_version_id: str | None = None  # 回滚时指向被复制版本
    roll_back: bool = False
    text_content: str | None = None
    content: bytes | None = field(default=None, repr=False)


@dataclass
class DocumentChangeEntity:
    """diff 单条记录。"""

    section: str
    change_type: str  # added | removed | changed
    before: str | None = None
    after: str | None = None


@dataclass
class DocumentDiffEntity:
    from_version: DocumentVersionEntity
    to_version: DocumentVersionEntity
    changes: list[DocumentChangeEntity] = field(default_factory=list)


# 与 OpenAPI §8.2 文档下载响应类型保持一致
BINARY_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def to_file_ref_dict(file_id: str, file_name: str, mime_type: str, size_bytes: int, sha256: str) -> dict[str, Any]:
    return {
        "id": file_id,
        "fileName": file_name,
        "mimeType": mime_type,
        "sizeBytes": size_bytes,
        "sha256": sha256,
        "scanStatus": "clean",
    }
