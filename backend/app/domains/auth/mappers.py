"""Contract mappers shared by authentication and user-management routes."""

from __future__ import annotations

from typing import Any

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": ["*"],
    "project_lead": ["projects:read", "projects:write", "bids:read", "bids:write", "bids:review", "users:read"],
    "reviewer": ["projects:read", "bids:read", "bids:review"],
    "member": ["projects:read", "bids:read"],
}


def user_to_data(user: Any, *, project_count: int = 0) -> dict[str, Any]:
    """Map a user ORM object to the locked camelCase ``User`` shape."""
    return {
        "id": str(user.id),
        "tenantId": str(user.tenant_id),
        "email": user.email,
        "name": user.name,
        "phone": user.phone,
        "role": user.role.value,
        "department": user.department,
        "status": user.status.value,
        "projectCount": project_count,
        "lastLoginAt": user.last_login_at,
        "version": 1,
        "createdAt": user.created_at,
        "updatedAt": user.updated_at,
    }
