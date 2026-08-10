"""M5 路由辅助：与 M6 http.py 风格一致。"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domains.bids.errors import DomainError
from app.domains.bids.ports import AuthPrincipal


def get_actor(request: Request) -> AuthPrincipal:
    """Single authentication dependency shared by every M5 router."""
    actor = getattr(request.state, "auth_principal", None)
    if not isinstance(actor, AuthPrincipal):
        raise DomainError(code="UNAUTHENTICATED", message="未认证")
    return actor


def request_id(request: Request) -> str:
    return request.headers.get("X-Request-Id") or str(uuid4())


def success(
    data: Any,
    *,
    request: Request,
    meta: dict[str, Any] | None = None,
    status_code: int = 200,
) -> JSONResponse:
    response_request_id = request_id(request)
    body: dict[str, Any] = {"success": True, "data": data, "requestId": response_request_id}
    if meta is not None:
        body["meta"] = meta
    return JSONResponse(
        status_code=status_code,
        content=body,
        headers={"X-Request-Id": response_request_id},
    )


def domain_http_exception(exc: DomainError, *, request: Request) -> DomainError:
    """Keep legacy router call sites while delegating formatting to the platform handler."""
    _ = request
    return exc


def parse_if_match(raw: str | None) -> int | None:
    if raw is None:
        return None
    value = raw.strip().strip('"')
    try:
        return int(value)
    except ValueError:
        return None


def require_if_match(raw: str | None) -> int:
    """按契约要求解析双引号包围的整数版本。"""
    from app.domains.bids.errors import validation_error

    if raw is None or len(raw) < 3 or not raw.startswith('"') or not raw.endswith('"'):
        raise validation_error(
            "If-Match 必填且格式必须为双引号包围的整数",
            field_errors=[{"field": "If-Match", "code": "FORMAT", "message": '示例："1"'}],
        )
    version = parse_if_match(raw)
    if version is None or version < 1:
        raise validation_error(
            "If-Match 格式错误",
            field_errors=[{"field": "If-Match", "code": "FORMAT", "message": "版本必须为正整数"}],
        )
    return version


def require_idempotency_key(raw: str | None) -> str:
    """校验所有异步/回滚动作共用的幂等键约束。"""
    from app.domains.bids.errors import validation_error

    key = (raw or "").strip()
    if not 8 <= len(key) <= 128:
        raise validation_error(
            "Idempotency-Key 必填且长度必须为 8 到 128 个字符",
            field_errors=[
                {
                    "field": "Idempotency-Key",
                    "code": "LENGTH",
                    "message": "请复用同一业务动作的 UUID/ULID 幂等键",
                }
            ],
        )
    return key
