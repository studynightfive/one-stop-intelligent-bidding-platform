"""Shared HTTP response helpers for the locked OpenAPI envelope."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel


def request_id(request: Request) -> str:
    """Return the caller request ID or create one for this response."""

    return request.headers.get("X-Request-Id") or str(uuid4())


def pagination_meta(*, page: int, page_size: int, total: int) -> dict[str, int]:
    """Build the one pagination shape used by every list endpoint."""

    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": (total + page_size - 1) // page_size if page_size else 0,
    }


def contract_data(value: Any) -> Any:
    """Recursively convert Pydantic/snake_case values to contract camelCase."""
    if isinstance(value, BaseModel):
        return contract_data(value.model_dump(exclude_none=True))
    if isinstance(value, dict):
        return {_camel_case(str(key)): contract_data(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [contract_data(item) for item in value]
    return value


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


def success_response(
    data: Any,
    *,
    request: Request,
    status_code: int = 200,
    meta: dict[str, Any] | None = None,
) -> JSONResponse:
    """Return a camelCase success envelope with a matching response header."""

    response_request_id = request_id(request)
    payload: dict[str, Any] = {
        "success": True,
        "data": data,
        "requestId": response_request_id,
    }
    if meta is not None:
        payload["meta"] = meta
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(payload),
        headers={"X-Request-Id": response_request_id},
    )
