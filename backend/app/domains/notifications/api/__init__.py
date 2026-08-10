"""通知API路由.

实现通知相关接口：
- GET /notifications - 通知列表
- PATCH /notifications/{id} - 标记已读
- POST /notifications/read-all - 全部已读
"""

import contextlib
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import AuthenticatedUser, DBSession
from app.core.errors import NotFoundError
from app.domains.notifications.models.notification import Notification, NotificationType
from app.domains.notifications.schemas.notification import (
    MarkAllReadResponse,
    NotificationListResponse,
    NotificationResponse,
)
from app.domains.notifications.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["通知"])


def _notification_to_response(notification: Notification) -> NotificationResponse:
    """将Notification模型转换为响应模型."""
    return NotificationResponse(
        id=notification.id,
        type=notification.type.value,
        title=notification.title,
        content=notification.content,
        is_read=notification.is_read,
        resource_type=notification.resource_type,
        resource_id=notification.resource_id,
        created_at=notification.created_at,
    )


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="通知列表",
    description="获取当前用户的通知列表。",
    responses={
        200: {"description": "成功"},
    },
)
async def list_notifications(
    current_user: AuthenticatedUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    notification_type: str | None = Query(None, alias="type"),
) -> NotificationListResponse:
    """获取通知列表."""
    notification_service = NotificationService(db)

    # 解析通知类型
    n_type = None
    if notification_type:
        with contextlib.suppress(ValueError):
            n_type = NotificationType(notification_type)

    offset = (page - 1) * page_size
    notifications, total, unread_count = await notification_service.list_notifications(
        user_id=UUID(current_user["id"]),
        tenant_id=UUID(current_user["tenant_id"]),
        notification_type=n_type,
        unread_only=unread_only,
        limit=page_size,
        offset=offset,
    )

    return NotificationListResponse(
        notifications=[_notification_to_response(n) for n in notifications],
        total=total,
        unread_count=unread_count,
    )


@router.patch(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="标记已读",
    description="将通知标记为已读或未读。",
    responses={
        200: {"description": "成功"},
        404: {"description": "通知不存在"},
    },
)
async def mark_notification_read(
    notification_id: UUID,
    current_user: AuthenticatedUser,
    db: DBSession,
) -> NotificationResponse:
    """标记通知已读."""
    notification_service = NotificationService(db)

    try:
        notification = await notification_service.mark_as_read(
            notification_id=notification_id,
            user_id=UUID(current_user["id"]),
        )
        return _notification_to_response(notification)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.post(
    "/read-all",
    response_model=MarkAllReadResponse,
    summary="全部已读",
    description="将所有通知标记为已读。",
    responses={
        200: {"description": "成功"},
    },
)
async def mark_all_read(
    current_user: AuthenticatedUser,
    db: DBSession,
) -> MarkAllReadResponse:
    """全部标记已读."""
    notification_service = NotificationService(db)

    updated_count = await notification_service.mark_all_as_read(
        user_id=UUID(current_user["id"]),
        tenant_id=UUID(current_user["tenant_id"]),
    )

    return MarkAllReadResponse(updated_count=updated_count)
