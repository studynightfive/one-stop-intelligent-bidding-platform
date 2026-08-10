"""通知API路由.

实现通知相关接口：
- GET /notifications - 通知列表
- PATCH /notifications/{id} - 标记已读
- POST /notifications/read-all - 全部已读
"""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from app.core.dependencies import AuthenticatedUser, DBSession
from app.core.errors import NotFoundError
from app.core.http import pagination_meta, success_response
from app.domains.notifications.models.notification import Notification, NotificationType
from app.domains.notifications.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["通知"])


def _notification_to_data(notification: Notification) -> dict[str, object]:
    """Map a notification to the locked camelCase contract shape."""

    data: dict[str, object] = {
        "id": str(notification.id),
        "type": notification.type.value,
        "title": notification.title,
        "content": notification.content,
        "isRead": notification.is_read,
        "createdAt": notification.created_at,
    }
    if notification.resource_type is not None:
        data["resourceType"] = notification.resource_type
    if notification.resource_id is not None:
        data["resourceId"] = str(notification.resource_id)
    return data


@router.get(
    "",
    summary="通知列表",
    description="获取当前用户的通知列表。",
    responses={
        200: {"description": "成功"},
    },
)
async def list_notifications(
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    unread_only: bool = Query(False, alias="unreadOnly"),
    notification_type: str | None = Query(None, alias="type"),
    sort_by: str = Query("createdAt", alias="sortBy", pattern="^createdAt$"),
    sort_order: str = Query("desc", alias="sortOrder", pattern="^(asc|desc)$"),
) -> JSONResponse:
    """获取通知列表."""
    notification_service = NotificationService(db)

    # 解析通知类型
    try:
        n_type = NotificationType(notification_type) if notification_type else None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "VALIDATION_ERROR", "message": "不支持的通知类型"},
        ) from exc

    offset = (page - 1) * page_size
    notifications, total, unread_count = await notification_service.list_notifications(
        user_id=UUID(current_user["id"]),
        tenant_id=UUID(current_user["tenant_id"]),
        notification_type=n_type,
        unread_only=unread_only,
        sort_order=sort_order,
        limit=page_size,
        offset=offset,
    )

    _ = unread_count, sort_by
    return success_response(
        [_notification_to_data(notification) for notification in notifications],
        request=request,
        meta=pagination_meta(page=page, page_size=page_size, total=total),
    )


@router.patch(
    "/{notification_id}",
    summary="标记已读",
    description="将通知标记为已读或未读。",
    responses={
        200: {"description": "成功"},
        404: {"description": "通知不存在"},
    },
)
async def mark_notification_read(
    notification_id: UUID,
    payload: dict[str, object],
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
    if_match: str = Header(..., alias="If-Match"),
) -> JSONResponse:
    """标记通知已读."""
    notification_service = NotificationService(db)
    if not if_match.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "VALIDATION_ERROR", "message": "If-Match 不能为空"},
        )
    if payload != {"isRead": True}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "VALIDATION_ERROR", "message": "isRead 必须为 true"},
        )

    try:
        notification = await notification_service.mark_as_read(
            notification_id=notification_id,
            user_id=UUID(current_user["id"]),
        )
        return success_response(_notification_to_data(notification), request=request)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.post(
    "/read-all",
    summary="全部已读",
    description="将所有通知标记为已读。",
    responses={
        200: {"description": "成功"},
    },
)
async def mark_all_read(
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> JSONResponse:
    """全部标记已读."""
    notification_service = NotificationService(db)

    updated_count = await notification_service.mark_all_as_read(
        user_id=UUID(current_user["id"]),
        tenant_id=UUID(current_user["tenant_id"]),
    )

    _ = idempotency_key
    return success_response({"updatedCount": updated_count}, request=request)
