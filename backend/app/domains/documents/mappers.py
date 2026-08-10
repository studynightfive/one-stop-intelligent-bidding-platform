"""Documents 实体 -> OpenAPI 契约 camelCase 字典。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domains.documents.entities import (
    DocumentEntity,
    DocumentVersionEntity,
)


def _dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.isoformat() + "Z"
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _file_ref_for_version(version: DocumentVersionEntity) -> dict[str, Any]:
    return {
        "id": version.file_id,
        "fileName": version.file_name,
        "mimeType": version.mime_type,
        "sizeBytes": version.size_bytes,
        "sha256": version.sha256,
        "scanStatus": "clean",
        "createdAt": _dt(version.created_at),
    }


def document_dict(entity: DocumentEntity) -> dict[str, Any]:
    latest = entity.versions[-1] if entity.versions else None
    data: dict[str, Any] = {
        "id": entity.id,
        "taskId": entity.task_id,
        "type": entity.doc_type,
        "currentVersion": entity.current_version,
        "createdAt": _dt(entity.created_at),
    }
    if latest is not None:
        data["latestFile"] = _file_ref_for_version(latest)
    return data


def document_version_dict(entity: DocumentVersionEntity) -> dict[str, Any]:
    return {
        "id": entity.id,
        "documentId": entity.document_id,
        "versionNumber": entity.version_number,
        "file": _file_ref_for_version(entity),
        "changeSummary": entity.change_summary,
        "createdBy": {"id": entity.created_by_id, "name": entity.created_by_name},
        "createdAt": _dt(entity.created_at),
    }


def document_diff_dict(
    *,
    from_version: DocumentVersionEntity,
    to_version: DocumentVersionEntity,
    changes: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "from": document_version_dict(from_version),
        "to": document_version_dict(to_version),
        "changes": changes,
    }
