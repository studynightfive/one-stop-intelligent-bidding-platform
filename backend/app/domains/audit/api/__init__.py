"""Tenant-scoped audit list and XLSX export routes."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response

from app.core.dependencies import AdminUser, DBSession
from app.core.http import pagination_meta, request_id, success_response
from app.core.xlsx import build_xlsx
from app.domains.audit.mappers import audit_event_to_data
from app.domains.audit.models.audit_event import AuditEvent
from app.domains.audit.services.audit_service import AuditService

router = APIRouter(prefix="/audit-events", tags=["审计"])


def _actor_filters(actor: str | None) -> tuple[UUID | None, str | None]:
    if not actor:
        return None, None
    try:
        return UUID(actor), None
    except ValueError:
        return None, actor


async def _query_events(
    *,
    db: DBSession,
    current_user: dict[str, str],
    actor: str | None,
    action: str | None,
    resource: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    sort_order: str,
    limit: int,
    offset: int,
) -> tuple[list[AuditEvent], int]:
    actor_id, actor_name = _actor_filters(actor)
    return await AuditService(db).list_events(
        tenant_id=UUID(current_user["tenant_id"]),
        actor_id=actor_id,
        actor_name=actor_name,
        action=action,
        resource=resource,
        start_date=date_from,
        end_date=date_to,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )


@router.get("")
async def list_audit_events(
    request: Request,
    current_user: AdminUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    sort_by: str = Query("createdAt", alias="sortBy", pattern="^createdAt$"),
    sort_order: str = Query("desc", alias="sortOrder", pattern="^(asc|desc)$"),
    actor: str | None = Query(None),
    action: str | None = Query(None),
    resource: str | None = Query(None),
    date_from: datetime | None = Query(None, alias="dateFrom"),
    date_to: datetime | None = Query(None, alias="dateTo"),
) -> JSONResponse:
    """Return real append-only audit events using the common page envelope."""
    events, total = await _query_events(
        db=db,
        current_user=current_user,
        actor=actor,
        action=action,
        resource=resource,
        date_from=date_from,
        date_to=date_to,
        sort_order=sort_order,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    _ = sort_by
    return success_response(
        [audit_event_to_data(event) for event in events],
        request=request,
        meta=pagination_meta(page=page, page_size=page_size, total=total),
    )


@router.get("/export")
async def export_audit_events(
    request: Request,
    current_user: AdminUser,
    db: DBSession,
    actor: str | None = Query(None),
    action: str | None = Query(None),
    resource: str | None = Query(None),
    date_from: datetime | None = Query(None, alias="dateFrom"),
    date_to: datetime | None = Query(None, alias="dateTo"),
) -> Response:
    """Export the current audit filters as a directly downloadable XLSX."""
    events, _ = await _query_events(
        db=db,
        current_user=current_user,
        actor=actor,
        action=action,
        resource=resource,
        date_from=date_from,
        date_to=date_to,
        sort_order="desc",
        limit=10_000,
        offset=0,
    )
    rows: list[list[object]] = [
        ["时间", "操作者", "操作者类型", "操作", "资源", "资源 ID", "摘要", "请求 ID", "IP 地址"]
    ]
    rows.extend(
        [
            event.created_at.isoformat(),
            event.actor_name,
            event.actor_type.value,
            event.action,
            event.aggregate_type,
            str(event.aggregate_id),
            event.summary,
            event.request_id,
            event.ip_address or "",
        ]
        for event in events
    )
    content = build_xlsx(rows, sheet_name="审计日志")
    response_request_id = request_id(request)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="audit-events.xlsx"',
            "X-File-Sha256": sha256(content).hexdigest(),
            "X-Request-Id": response_request_id,
        },
    )
