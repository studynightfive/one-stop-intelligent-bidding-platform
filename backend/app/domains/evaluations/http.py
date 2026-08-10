"""M6 路由辅助：统一成功 envelope 与领域错误映射（不替代 M4 全局中间件）。"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.domains.evaluations.errors import DomainError


def request_id(request: Request) -> str:
    return request.headers.get("X-Request-Id") or str(uuid4())


def success(data: Any, *, request: Request, meta: dict[str, Any] | None = None, status_code: int = 200) -> JSONResponse:
    body: dict[str, Any] = {"success": True, "data": data, "requestId": request_id(request)}
    if meta is not None:
        body["meta"] = meta
    return JSONResponse(status_code=status_code, content=body)


def domain_http_exception(exc: DomainError, *, request: Request) -> HTTPException:
    status_map = {
        "VALIDATION_ERROR": 422,
        "UNAUTHENTICATED": 401,
        "TOKEN_EXPIRED": 401,
        "FORBIDDEN": 403,
        "NOT_FOUND": 404,
        "CONFLICT": 409,
        "VERSION_CONFLICT": 409,
        "RATE_LIMITED": 429,
        "DEADLINE_PASSED": 409,
        "INVALID_STATE_TRANSITION": 409,
        "FILE_REJECTED": 422,
        "VIRUS_DETECTED": 422,
        "AI_PROVIDER_UNAVAILABLE": 503,
        "JOB_FAILED": 500,
        "INTERNAL_ERROR": 500,
    }
    error: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.details:
        error["details"] = exc.details
    if exc.field_errors:
        error["fieldErrors"] = exc.field_errors
    return HTTPException(
        status_code=status_map.get(exc.code, 400),
        detail={"success": False, "error": error, "requestId": request_id(request)},
    )


def parse_if_match(raw: str | None) -> int | None:
    if raw is None:
        return None
    value = raw.strip().strip('"')
    try:
        return int(value)
    except ValueError:
        return None
