"""Map audit persistence models to the locked HTTP contract."""

from __future__ import annotations

from typing import Any

from app.domains.audit.models.audit_event import AuditEvent


def _changes_to_data(changes: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    if not changes:
        return None
    result: list[dict[str, Any]] = []
    for field, value in changes.items():
        if isinstance(value, dict) and ("old" in value or "new" in value):
            old_value = value.get("old")
            new_value = value.get("new")
        else:
            old_value = None
            new_value = value
        result.append({"field": field, "oldValue": old_value, "newValue": new_value})
    return result


def audit_event_to_data(event: AuditEvent) -> dict[str, Any]:
    """Return one camelCase ``AuditEvent`` response item."""
    data: dict[str, Any] = {
        "id": str(event.id),
        "tenantId": str(event.tenant_id),
        "aggregateType": event.aggregate_type,
        "aggregateId": str(event.aggregate_id),
        "actorType": event.actor_type.value,
        "actorName": event.actor_name,
        "action": event.action,
        "summary": event.summary,
        "requestId": event.request_id,
        "createdAt": event.created_at,
    }
    optional = {
        "actorId": str(event.actor_id) if event.actor_id else None,
        "targetType": event.target_type,
        "targetId": str(event.target_id) if event.target_id else None,
        "changes": _changes_to_data(event.changes),
        "ipAddress": event.ip_address,
    }
    data.update({key: value for key, value in optional.items() if value is not None})
    return data
