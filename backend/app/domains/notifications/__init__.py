"""M4 公共平台后端 - notifications 领域."""

from app.domains.notifications.models.notification import (
    Notification,
    NotificationType,
)
from app.domains.notifications.services.notification_service import NotificationService

__all__ = [
    "Notification",
    "NotificationType",
    "NotificationService",
]
