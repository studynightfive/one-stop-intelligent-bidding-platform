"""健康检查与实时票据测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.domains import health
from app.domains.health import DependencyHealth
from app.domains.jobs.services import realtime_ticket_service as realtime_module


@pytest.mark.asyncio
async def test_liveness_and_readiness(monkeypatch: pytest.MonkeyPatch) -> None:
    assert (await health.liveness()).status == "ok"

    monkeypatch.setattr(health, "check_database", AsyncMock(return_value=DependencyHealth(name="db", status="ok")))
    monkeypatch.setattr(health, "check_redis", AsyncMock(return_value=DependencyHealth(name="redis", status="down")))
    monkeypatch.setattr(health, "check_minio", AsyncMock(return_value=DependencyHealth(name="minio", status="down")))
    readiness = await health.readiness()
    assert readiness.status == "degraded"
    assert len(readiness.dependencies) == 3

    monkeypatch.setattr(health, "check_database", AsyncMock(return_value=DependencyHealth(name="db", status="down")))
    assert (await health.readiness()).status == "down"


@pytest.mark.asyncio
async def test_dependency_health_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    assert (await health.check_database()).status == "ok"

    broken_engine = SimpleNamespace(connect=Mock(side_effect=RuntimeError("database unavailable")))
    monkeypatch.setattr(health, "async_engine", broken_engine)
    assert (await health.check_database()).status == "down"

    redis_client = SimpleNamespace(ping=AsyncMock())
    monkeypatch.setattr("app.core.redis.redis_client.get_client", AsyncMock(return_value=redis_client))
    assert (await health.check_redis()).status == "ok"
    redis_client.ping.side_effect = RuntimeError("redis unavailable")
    assert (await health.check_redis()).status == "down"

    minio_client = SimpleNamespace(bucket_exists=Mock(return_value=True))
    monkeypatch.setattr("minio.Minio", lambda **_kwargs: minio_client)
    assert (await health.check_minio()).status == "ok"
    minio_client.bucket_exists.side_effect = RuntimeError("minio unavailable")
    assert (await health.check_minio()).status == "down"


@pytest.mark.asyncio
async def test_realtime_ticket_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SimpleNamespace(
        hset=AsyncMock(return_value=1),
        expire=AsyncMock(return_value=True),
        eval=AsyncMock(return_value=1),
        delete=AsyncMock(return_value=1),
    )
    monkeypatch.setattr(realtime_module.redis_client, "get_client", AsyncMock(return_value=client))
    service = realtime_module.RealtimeTicketService()
    user_id = uuid4()
    tenant_id = uuid4()
    token, expires_at = await service.create_ticket(user_id, tenant_id, "internal")
    assert token
    assert expires_at.tzinfo is not None

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "type": "websocket_ticket",
        "channel": "internal",
        "ticket_id": "ticket-1",
    }
    monkeypatch.setattr("app.core.security.jwt.verify_token", lambda *_args, **_kwargs: payload)
    validated = await service.validate_ticket(token)
    assert validated and validated["ticket_id"] == "ticket-1"

    client.eval.return_value = 0
    assert await service.validate_ticket(token) is None
    monkeypatch.setattr(
        "app.core.security.jwt.verify_token",
        lambda *_args, **_kwargs: {**payload, "type": "access"},
    )
    assert await service.validate_ticket(token) is None
    monkeypatch.setattr(
        "app.core.security.jwt.verify_token",
        lambda *_args, **_kwargs: {**payload, "ticket_id": ""},
    )
    assert await service.validate_ticket(token) is None
    monkeypatch.setattr(
        "app.core.security.jwt.verify_token",
        Mock(side_effect=ValueError("invalid")),
    )
    assert await service.validate_ticket("bad") is None

    await service.invalidate_ticket("ticket-1")
    client.delete.assert_awaited_once()
