"""M5 端口协议：M4 平台端口稳定 import；M5 自身额外暴露 ``BidTaskSnapshotPort`` 实现位置。

M4 端口来自 M6 ``evaluations.ports``（已稳定且 L0 锁定）。M5 不重写这些类型，
仅做 import 入口让 L0 / M6 都能引用。
"""

from __future__ import annotations

from app.domains.evaluations.ports import (  # noqa: F401
    AuditEventInput,
    AuditServicePort,
    AuthPrincipal,
    BidMaterialSnapshot,
    BidTaskSnapshot,
    BidTaskSnapshotPort,
    FileRefSnapshot,
    FileServicePort,
    JobDispatcherPort,
    JobRefSnapshot,
    NotificationInput,
    NotificationServicePort,
    RecordingPorts,
    Role,
)

__all__ = [
    "AuthPrincipal",
    "AuditEventInput",
    "AuditServicePort",
    "BidMaterialSnapshot",
    "BidTaskSnapshot",
    "BidTaskSnapshotPort",
    "FileRefSnapshot",
    "FileServicePort",
    "JobDispatcherPort",
    "JobRefSnapshot",
    "NotificationInput",
    "NotificationServicePort",
    "RecordingPorts",
    "Role",
]
