"""供应商门户 API 路由（§8.5）。由 L0 在中央 Router include。"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, Header, Request, Response

from app.domains.evaluations.binary import binary_file_response
from app.domains.evaluations.container import M6Container
from app.domains.evaluations.errors import DomainError
from app.domains.evaluations.http import domain_http_exception, success
from app.domains.evaluations.ports import PortalPrincipal
from app.domains.evaluations.router import get_container
from app.domains.portal.service import PORTAL_REFRESH_COOKIE

router = APIRouter(prefix="/portal", tags=["portal"])
_T = TypeVar("_T")


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    import os

    # TestClient / 本地 HTTP 无法携带 Secure Cookie；生产再开启
    secure = os.getenv("ENVIRONMENT", "development").lower() in {"production", "prod"}
    response.set_cookie(
        key=PORTAL_REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/api/v1/portal",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=PORTAL_REFRESH_COOKIE, path="/api/v1/portal")


def get_portal_principal(
    request: Request,
    authorization: str | None = Header(default=None),
    container: M6Container = Depends(get_container),
) -> PortalPrincipal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise domain_http_exception(DomainError(code="UNAUTHENTICATED", message="缺少门户令牌"), request=request)
    token = authorization.split(" ", 1)[1].strip()
    try:
        return container.portal.resolve_principal(token)
    except DomainError as exc:
        raise domain_http_exception(exc, request=request) from exc


async def _run(request: Request, coro: Awaitable[_T]) -> _T:
    try:
        return await coro
    except DomainError as exc:
        raise domain_http_exception(exc, request=request) from exc


@router.post("/session/exchange")
async def exchange(
    request: Request,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
) -> Response:
    data = await _run(request, container.portal.exchange(str(payload.get("inviteCode", ""))))
    refresh = data.pop("refreshToken", None)
    data.pop("refreshTokenExpiresAt", None)
    response = success(data, request=request)
    if refresh:
        _set_refresh_cookie(response, refresh)
    return response


@router.post("/session/refresh")
async def refresh(
    request: Request,
    container: M6Container = Depends(get_container),
) -> Response:
    refresh_token = request.cookies.get(PORTAL_REFRESH_COOKIE)
    if not refresh_token:
        raise domain_http_exception(
            DomainError(code="UNAUTHENTICATED", message="缺少 Portal Refresh Cookie"),
            request=request,
        )
    data = await _run(request, container.portal.refresh(refresh_token))
    refresh_new = data.pop("refreshToken", None)
    data.pop("refreshTokenExpiresAt", None)
    response = success(data, request=request)
    if refresh_new:
        _set_refresh_cookie(response, refresh_new)
    return response


@router.post("/session/logout")
async def logout(
    request: Request,
    authorization: str | None = Header(default=None),
    container: M6Container = Depends(get_container),
) -> Response:
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    refresh_token = request.cookies.get(PORTAL_REFRESH_COOKIE)
    data = await _run(request, container.portal.logout(token, refresh_token))
    response = success(data, request=request)
    _clear_refresh_cookie(response)
    return response


@router.get("/me")
async def me(
    request: Request,
    portal: PortalPrincipal = Depends(get_portal_principal),
    container: M6Container = Depends(get_container),
) -> Response:
    data = await _run(request, container.portal.me(portal))
    return success(data, request=request)


@router.get("/materials")
async def materials(
    request: Request,
    portal: PortalPrincipal = Depends(get_portal_principal),
    container: M6Container = Depends(get_container),
) -> Response:
    data = await _run(request, container.portal.list_materials(portal))
    return success(data, request=request)


@router.put("/materials/{materialId}/file")
async def put_file(
    request: Request,
    materialId: str,
    payload: dict[str, Any],
    portal: PortalPrincipal = Depends(get_portal_principal),
    container: M6Container = Depends(get_container),
) -> Response:
    data = await _run(request, container.portal.put_material_file(portal, materialId, str(payload.get("fileId", ""))))
    return success(data, request=request)


@router.delete("/materials/{materialId}/file")
async def delete_file(
    request: Request,
    materialId: str,
    portal: PortalPrincipal = Depends(get_portal_principal),
    container: M6Container = Depends(get_container),
) -> Response:
    data = await _run(request, container.portal.delete_material_file(portal, materialId))
    return success(data, request=request)


@router.put("/draft")
async def save_draft(
    request: Request,
    payload: dict[str, Any],
    portal: PortalPrincipal = Depends(get_portal_principal),
    container: M6Container = Depends(get_container),
) -> Response:
    data = await _run(request, container.portal.save_draft(portal, payload))
    return success(data, request=request)


@router.post("/submit")
async def submit(
    request: Request,
    payload: dict[str, Any],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    portal: PortalPrincipal = Depends(get_portal_principal),
    container: M6Container = Depends(get_container),
) -> Response:
    data = await _run(
        request,
        container.portal.submit(portal, confirmed=bool(payload.get("confirmed")), idempotency_key=idempotency_key),
    )
    return success(data, request=request)


@router.get("/receipt")
async def receipt(
    request: Request,
    portal: PortalPrincipal = Depends(get_portal_principal),
    container: M6Container = Depends(get_container),
) -> Response:
    try:
        pdf, file_name, digest = await container.portal.build_receipt_pdf(portal)
    except DomainError as exc:
        raise domain_http_exception(exc, request=request) from exc
    return binary_file_response(
        content=pdf,
        file_name=file_name,
        content_type="application/pdf",
        sha256=digest,
    )


@router.get("/notices")
async def notices(
    request: Request,
    portal: PortalPrincipal = Depends(get_portal_principal),
    container: M6Container = Depends(get_container),
) -> Response:
    data = await _run(request, container.portal.list_notices(portal))
    return success(data, request=request)


@router.post("/notices/{noticeId}/respond")
async def respond_notice(
    request: Request,
    noticeId: str,
    payload: dict[str, Any],
    portal: PortalPrincipal = Depends(get_portal_principal),
    container: M6Container = Depends(get_container),
) -> Response:
    bindings = payload.get("fileBindings") or []
    data = await _run(request, container.portal.respond_notice(portal, noticeId, bindings))
    return success(data, request=request)


@router.get("/price-rounds")
async def price_rounds(
    request: Request,
    portal: PortalPrincipal = Depends(get_portal_principal),
    container: M6Container = Depends(get_container),
) -> Response:
    data = await _run(request, container.portal.list_price_rounds(portal))
    return success(data, request=request)


@router.post("/price-rounds/{roundId}/quotes")
async def submit_quote(
    request: Request,
    roundId: str,
    payload: dict[str, Any],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    portal: PortalPrincipal = Depends(get_portal_principal),
    container: M6Container = Depends(get_container),
) -> Response:
    amount = str(getattr(payload.get("amount"), "root", payload.get("amount", "")))
    currency = str(getattr(payload.get("currency"), "root", payload.get("currency", "CNY")))
    data = await _run(
        request,
        container.pricing.submit_quote(
            portal, roundId, amount=amount, currency=currency, idempotency_key=idempotency_key
        ),
    )
    return success(data, request=request)


@router.get("/activity")
async def activity(
    request: Request,
    page: int = 1,
    pageSize: int = 20,
    portal: PortalPrincipal = Depends(get_portal_principal),
    container: M6Container = Depends(get_container),
) -> Response:
    data, meta = await _run(request, container.portal.list_activity(portal, page=page, page_size=pageSize))
    return success(data, request=request, meta=meta)
