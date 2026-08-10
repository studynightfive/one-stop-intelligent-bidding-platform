"""资质库 OpenAPI 路由（§8.3 中的 10 个操作）。"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, TypeVar, cast
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.contracts.generated.models import CreateQualificationRequest, UpdateQualificationRequest
from app.domains.bids.errors import DomainError
from app.domains.bids.http import domain_http_exception, get_actor, request_id, require_if_match, success
from app.domains.bids.ports import AuthPrincipal
from app.domains.qualifications.service import QualificationService

router = APIRouter(tags=["资质与片段库"])
_T = TypeVar("_T")


def get_service(request: Request) -> QualificationService:
    container = getattr(request.app.state, "m5", None)
    service = getattr(container, "qualifications", None)
    if service is None:
        raise RuntimeError("M5 qualifications 未装配：请设置 app.state.m5.qualifications")
    return cast(QualificationService, service)


async def _run(request: Request, operation: Awaitable[_T]) -> _T:
    try:
        return await operation
    except DomainError as exc:
        raise domain_http_exception(exc, request=request) from exc


def _if_match(request: Request, value: str | None) -> int:
    try:
        return require_if_match(value)
    except DomainError as exc:
        raise domain_http_exception(exc, request=request) from exc


@router.get("/qualifications/stats")
async def qualification_stats(
    request: Request,
    service: QualificationService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, service.stats(actor)), request=request)


@router.get("/qualifications")
async def list_qualifications(
    request: Request,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    sortBy: str | None = None,
    sortOrder: str = Query(default="desc", pattern="^(asc|desc)$"),
    keyword: str | None = Query(default=None, min_length=1),
    status: str | None = None,
    category: str | None = None,
    expiresWithinDays: int | None = Query(default=None, ge=0),
    service: QualificationService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data, meta = await _run(
        request,
        service.list_qualifications(
            actor,
            page=page,
            page_size=pageSize,
            sort_by=sortBy,
            sort_order=sortOrder,
            keyword=keyword,
            status=status,
            category=category,
            expires_within_days=expiresWithinDays,
        ),
    )
    return success(data, request=request, meta=meta)


@router.post("/qualifications", status_code=201)
async def create_qualification(
    request: Request,
    payload: CreateQualificationRequest,
    service: QualificationService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, service.create(actor, payload.model_dump(mode="python")))
    return success(data, request=request, status_code=201)


@router.post("/qualifications/imports", status_code=202)
async def import_qualifications(
    request: Request,
    payload: dict[str, Any],
    service: QualificationService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, service.import_file(actor, payload))
    return success(data, request=request, status_code=202)


@router.get("/qualifications/import-template")
async def qualification_import_template(
    request: Request,
    service: QualificationService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    content, digest = await _run(request, service.import_template(actor))
    rid = request_id(request)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="qualification-import-template.xlsx"',
            "X-File-Sha256": digest,
            "X-Request-Id": rid,
        },
    )


@router.post("/qualifications/{id}/versions")
async def add_qualification_version(
    request: Request,
    id: str,
    payload: dict[str, Any],
    service: QualificationService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, service.add_version(actor, id, payload))
    return success(data, request=request)


@router.get("/qualifications/{id}/download")
async def download_qualification(
    request: Request,
    id: str,
    service: QualificationService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    url, file_name, digest, mime_type = await _run(request, service.download(actor, id))
    rid = request_id(request)
    return RedirectResponse(
        url=url,
        status_code=307,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(file_name)}",
            "Content-Type": mime_type,
            "X-File-Sha256": digest,
            "X-Request-Id": rid,
        },
    )


@router.get("/qualifications/{id}")
async def get_qualification(
    request: Request,
    id: str,
    service: QualificationService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, service.get(actor, id)), request=request)


@router.patch("/qualifications/{id}")
async def update_qualification(
    request: Request,
    id: str,
    payload: UpdateQualificationRequest,
    if_match: str | None = Header(default=None, alias="If-Match"),
    service: QualificationService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        service.update(
            actor,
            id,
            payload.model_dump(mode="python", exclude_unset=True),
            expected_version=_if_match(request, if_match),
        ),
    )
    return success(data, request=request)


@router.delete("/qualifications/{id}", status_code=204)
async def delete_qualification(
    request: Request,
    id: str,
    payload: dict[str, Any],
    service: QualificationService = Depends(get_service),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    await _run(
        request,
        service.delete(actor, id, payload),
    )
    return Response(status_code=204, headers={"X-Request-Id": request_id(request)})
