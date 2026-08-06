"""L0 独占的 SQLAlchemy 模型基类与中央注册点。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有领域 ORM 模型必须继承的唯一基类。"""


# M4/M5/M6 的模型 PR 合并后，由 L0 在此添加显式 import。
# Alembic 不允许依赖隐式扫描或跨领域 import 副作用。
