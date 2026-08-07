"""数据库会话和连接管理.

使用 SQLAlchemy 2.0 异步模式，支持：
- 读写分离（未来扩展）
- 连接池
- 自动重试
- 事务管理
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings


def _create_async_engine() -> AsyncEngine:
    """创建异步数据库引擎."""
    is_sqlite = settings.database_url.startswith("sqlite")

    if is_sqlite:
        # SQLite 使用 NullPool，不支持 pool_kwargs
        return create_async_engine(
            settings.database_url,
            poolclass=NullPool,
            echo=settings.debug,
            future=True,
        )

    # PostgreSQL 使用 QueuePool
    return create_async_engine(
        settings.database_url,
        poolclass=QueuePool,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.debug,
        future=True,
    )


# 全局异步引擎
async_engine: AsyncEngine = _create_async_engine()

# 异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy声明性基类.

    所有模型必须继承此类。
    """
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖注入函数.

    用法:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的上下文管理器（用于非依赖注入场景）."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库（创建所有表）.

    仅用于测试和开发环境。
    生产环境使用 Alembic 迁移。
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库连接."""
    await async_engine.dispose()


# 数据库事件监听
@event.listens_for(async_engine.sync_engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """数据库连接建立时的回调."""
    pass


@event.listens_for(async_engine.sync_engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """数据库连接检出时的回调."""
    pass
