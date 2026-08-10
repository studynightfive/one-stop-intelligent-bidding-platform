"""健康检查API.

提供应用健康状态检查接口。
"""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.database import async_engine

router = APIRouter(tags=["健康检查"])


class HealthResponse(BaseModel):
    """健康检查响应."""

    status: str = Field(description="健康状态: ok, degraded, down")
    timestamp: str = Field(description="检查时间 ISO格式")


class DependencyHealth(BaseModel):
    """依赖服务健康状态."""

    name: str = Field(description="服务名称")
    status: str = Field(description="状态: ok, down")
    latency_ms: float | None = Field(default=None, description="响应延迟(ms)")
    message: str | None = Field(default=None, description="错误信息")


class ReadinessResponse(BaseModel):
    """就绪检查响应."""

    status: str = Field(description="总体状态: ok, degraded, down")
    dependencies: list[DependencyHealth] = Field(description="依赖服务状态")
    checked_at: str = Field(description="检查时间 ISO格式")


@router.get(
    "/health/live",
    response_model=HealthResponse,
    summary="存活检查",
    description="检查应用是否存活。用于Kubernetes livenessProbe。",
    responses={
        200: {"description": "应用存活"},
    },
)
async def liveness() -> HealthResponse:
    """存活检查.

    简单检查应用进程是否在运行。
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="就绪检查",
    description="检查应用是否就绪，所有依赖是否可用。用于Kubernetes readinessProbe。",
    responses={
        200: {"description": "应用就绪"},
        503: {"description": "应用未就绪"},
    },
)
async def readiness() -> ReadinessResponse:
    """就绪检查.

    检查数据库、Redis、MinIO等依赖服务是否可用。
    返回 degraded 状态表示部分依赖不可用但核心功能可用。
    """
    dependencies: list[DependencyHealth] = []
    overall_status = "ok"

    # 1. 检查数据库
    db_status = await check_database()
    dependencies.append(db_status)
    if db_status.status == "down":
        overall_status = "down"

    # 2. 检查Redis
    redis_status = await check_redis()
    dependencies.append(redis_status)
    if redis_status.status == "down" and overall_status == "ok":
        overall_status = "degraded"

    # 3. 检查MinIO
    minio_status = await check_minio()
    dependencies.append(minio_status)
    if minio_status.status == "down" and overall_status == "ok":
        overall_status = "degraded"

    return ReadinessResponse(
        status=overall_status,
        dependencies=dependencies,
        checked_at=datetime.now(UTC).isoformat(),
    )


async def check_database() -> DependencyHealth:
    """检查数据库连接."""
    import time

    try:
        start = time.perf_counter()
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        return DependencyHealth(
            name="postgres",
            status="ok",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return DependencyHealth(
            name="postgres",
            status="down",
            message=str(e),
        )


async def check_redis() -> DependencyHealth:
    """检查Redis连接."""
    import time

    try:
        from app.core.redis import redis_client

        start = time.perf_counter()
        client = await redis_client.get_client()
        await client.ping()
        latency = (time.perf_counter() - start) * 1000
        return DependencyHealth(
            name="redis",
            status="ok",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return DependencyHealth(
            name="redis",
            status="down",
            message=str(e),
        )


async def check_minio() -> DependencyHealth:
    """检查MinIO连接."""
    import time

    try:
        from app.core.config import settings as app_settings

        start = time.perf_counter()
        from minio import Minio

        client = Minio(
            endpoint=app_settings.minio_endpoint.replace("http://", "").replace("https://", ""),
            access_key=app_settings.minio_access_key,
            secret_key=app_settings.minio_secret_key,
            secure=app_settings.minio_secure,
        )
        # 简单检查：尝试获取bucket信息
        _ = client.bucket_exists(app_settings.minio_bucket)
        latency = (time.perf_counter() - start) * 1000
        return DependencyHealth(
            name="minio",
            status="ok",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return DependencyHealth(
            name="minio",
            status="down",
            message=str(e),
        )
