"""Pytest 配置和共享 fixtures.

测试环境配置必须在导入任何应用模块之前设置。
"""

import os
from collections.abc import AsyncGenerator

# === 必须在导入任何 app 模块之前设置环境变量 ===
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["JWT_PRIVATE_KEY_PATH"] = "./jwt_private_key.pem"
os.environ["JWT_PUBLIC_KEY_PATH"] = "./jwt_public_key.pem"
os.environ["MODEL_MASTER_KEY_PATH"] = "./model_master_key.bin"
os.environ["CORS_ORIGINS"] = '["http://localhost:3000"]'

import pytest
import pytest_asyncio
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base

# === 为 SQLite 替换 JSONB 类型 ===


def _patch_jsonb_for_sqlite() -> None:
    """将所有 JSONB 列替换为 JSON 以支持 SQLite 测试."""
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON().with_variant(JSONB(), "postgresql")


# === Database ===


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话.

    使用内存 SQLite 数据库，每次测试创建独立连接。
    """
    # 在创建表之前先 patch JSONB
    _patch_jsonb_for_sqlite()

    # 创建测试数据库引擎
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 创建会话工厂
    async_session_factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # 创建会话
    async with async_session_factory() as session:
        yield session

    # 清理：关闭引擎
    await engine.dispose()


# === Test Client ===


@pytest.fixture
def anyio_backend() -> str:
    """指定 asyncio 作为 anyio 后端."""
    return "asyncio"


# === 辅助函数 ===


def create_test_user_data(
    email: str = "test@example.com",
    name: str = "Test User",
    role: str = "member",
) -> dict:
    """创建测试用户数据."""
    return {
        "email": email,
        "name": name,
        "password": "Test1234",
        "role": role,
        "department": "Test Department",
    }


def create_test_tenant_data(
    name: str = "Test Tenant",
) -> dict:
    """创建测试租户数据."""
    return {
        "name": name,
    }
