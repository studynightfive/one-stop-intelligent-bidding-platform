"""L0 独占的 SQLAlchemy 模型基类与中央注册点。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有领域 ORM 模型必须继承的唯一基类。"""


# M4/M5/M6 的模型 PR 合并后，由 L0 在此添加显式 import。
# Alembic 不允许依赖隐式扫描或跨领域 import 副作用。

# =============================================================================
# M4 公共平台后端 - 模型注册
# =============================================================================

# 用户认证领域
from app.domains.auth.models.user import User  # noqa: F401

# 文件平台领域
from app.domains.files.models.file import File, FileUploadSession  # noqa: F401

# 任务领域
from app.domains.jobs.models.job import Job  # noqa: F401

# 通知领域
from app.domains.notifications.models.notification import Notification  # noqa: F401

# 审计领域
from app.domains.audit.models.audit_event import AuditEvent  # noqa: F401
