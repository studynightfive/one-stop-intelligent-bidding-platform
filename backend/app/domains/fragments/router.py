"""片段库 HTTP Router；由 M5 容器提供服务实例。"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from app.domains.bids.errors import DomainError
from app.domains.bids.http import domain_http_exception, get_actor, request_id, require_if_match, success
from app.domains.bids.ports import AuthPrincipal
from app.domains.fragments.service import FragmentService

router = APIRouter(tags=["fragments"])
_T = TypeVar("_T")


def get_service(request: Request) -> FragmentService:
    container = getattr(request.app.state, "m5", None)
    service = getattr(container, "fragments", None)
    if not isinstance(service, FragmentService):
        raise RuntimeError("M5 fragments 服务未装配：请设置 request.app.state.m5.fragments")
    return service


async def _run(request: Request, operation: Awaitable[_T]) -> _T:
    try:
        return await operation
    except DomainError as exc:
        raise domain_http_exception(exc, request=request) from exc


@router.get("/fragments/stats")
async def fragment_stats(
    request: Request,
    service: FragmentService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, service.stats(actor)), request=request)


@router.get("/fragments")
async def list_fragments(
    request: Request,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    sortBy: str | None = None,
    sortOrder: str | None = None,
    keyword: str | None = None,
    category: str | None = None,
    searchMode: str | None = None,
    service: FragmentService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data, meta = await _run(
        request,
        service.list_fragments(
            actor,
            page=page,
            page_size=pageSize,
            sort_by=sortBy,
            sort_order=sortOrder,
            keyword=keyword,
            category=category,
            search_mode=searchMode,
        ),
    )
    return success(data, request=request, meta=meta)


@router.post("/fragments", status_code=201)
async def create_fragment(
    request: Request,
    payload: dict[str, Any],
    service: FragmentService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, service.create(actor, payload)), request=request, status_code=201)


@router.post("/fragments/semantic-search")
async def semantic_search(
    request: Request,
    payload: dict[str, Any],
    service: FragmentService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, service.semantic_search(actor, payload)), request=request)


@router.get("/fragments/{id}")
async def get_fragment(
    request: Request,
    id: str,
    service: FragmentService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, service.get(actor, id)), request=request)


@router.patch("/fragments/{id}")
async def update_fragment(
    request: Request,
    id: str,
    payload: dict[str, Any],
    if_match: str | None = Header(default=None, alias="If-Match"),
    service: FragmentService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    try:
        version = require_if_match(if_match)
    except DomainError as exc:
        raise domain_http_exception(exc, request=request) from exc
    data = await _run(request, service.update(actor, id, payload, if_match=version))
    return success(data, request=request)


@router.delete("/fragments/{id}", status_code=204)
async def delete_fragment(
    request: Request,
    id: str,
    payload: dict[str, Any],
    service: FragmentService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    await _run(request, service.delete(actor, id, payload))
    response_request_id = request_id(request)
    return Response(status_code=204, headers={"X-Request-Id": response_request_id})


@router.post("/fragments/{id}/versions")
async def add_fragment_version(
    request: Request,
    id: str,
    payload: dict[str, Any],
    service: FragmentService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, service.add_version(actor, id, payload)), request=request)


@router.post("/fragments/{id}/references")
async def add_fragment_reference(
    request: Request,
    id: str,
    payload: dict[str, Any],
    service: FragmentService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, service.add_reference(actor, id, payload)), request=request)
