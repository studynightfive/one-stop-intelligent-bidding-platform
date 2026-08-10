"""M5 bid-task HTTP API and the aggregate router for all four M5 domains."""

from __future__ import annotations

from collections.abc import Awaitable, Mapping
from hashlib import sha256
from typing import Any, TypeVar, cast
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.domains.bids.container import M5BidsContainer
from app.domains.bids.errors import DomainError
from app.domains.bids.http import domain_http_exception, get_actor, request_id, require_if_match, success
from app.domains.bids.ports import AuthPrincipal, Role
from app.domains.fragments.router import router as fragments_router
from app.domains.qualifications.router import router as qualifications_router

router = APIRouter(tags=["bids"])
_T = TypeVar("_T")


def get_container(request: Request) -> M5BidsContainer:
    container = getattr(request.app.state, "m5", None)
    if not isinstance(container, M5BidsContainer):
        raise RuntimeError("M5 container 未装配：请由 L0 设置 app.state.m5")
    return container


def auth_principal_from_context(current_user: Mapping[str, Any]) -> AuthPrincipal:
    """Map the L0 authenticated-user context to M5's stable principal."""
    user_id = current_user.get("id")
    tenant_id = current_user.get("tenant_id")
    if not user_id or not tenant_id:
        raise DomainError(code="UNAUTHENTICATED", message="认证上下文缺少用户或租户标识")
    raw_role = str(current_user.get("role", "member"))
    if raw_role not in {"admin", "project_lead", "member", "reviewer"}:
        raise DomainError(code="FORBIDDEN", message="当前用户角色无权访问投标工作台")
    permissions = tuple(str(item) for item in current_user.get("permissions", ()))
    return AuthPrincipal(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        name=str(current_user.get("name") or current_user.get("email") or "用户"),
        role=cast(Role, raw_role),
        permissions=permissions,
    )


async def _run(request: Request, operation: Awaitable[_T]) -> _T:
    try:
        return await operation
    except DomainError as exc:
        raise domain_http_exception(exc, request=request) from exc


@router.get("/bid-tasks/stats")
async def bid_task_stats(
    request: Request,
    keyword: str | None = None,
    status: str | None = None,
    assigneeId: str | None = None,
    quickFilter: str | None = None,
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.bids.stats(
            actor,
            keyword=keyword,
            status=status,
            assignee_id=assigneeId,
            quick_filter=quickFilter,
        ),
    )
    return success(data, request=request)


@router.get("/bid-tasks")
async def list_bid_tasks(
    request: Request,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    assigneeId: str | None = None,
    quickFilter: str | None = None,
    sortBy: str | None = None,
    sortOrder: str = "desc",
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data, meta = await _run(
        request,
        container.bids.list_tasks(
            actor,
            page=page,
            page_size=pageSize,
            keyword=keyword,
            status=status,
            assignee_id=assigneeId,
            quick_filter=quickFilter,
            sort_by=sortBy,
            sort_order=sortOrder,
        ),
    )
    return success(data, request=request, meta=meta)


@router.post("/bid-tasks", status_code=201)
async def create_bid_task(
    request: Request,
    payload: dict[str, Any],
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(
        await _run(request, container.bids.create(actor, payload)),
        request=request,
        status_code=201,
    )


@router.get("/bid-tasks/board")
async def bid_task_board(
    request: Request,
    keyword: str | None = None,
    status: str | None = None,
    assigneeId: str | None = None,
    quickFilter: str | None = None,
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.bids.board(
            actor,
            keyword=keyword,
            status=status,
            assignee_id=assigneeId,
            quick_filter=quickFilter,
        ),
    )
    return success(data, request=request)


@router.get("/bid-tasks/{taskId}")
async def get_bid_task(
    request: Request,
    taskId: str,
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, container.bids.get_detail(actor, taskId)), request=request)


@router.patch("/bid-tasks/{taskId}")
async def update_bid_task(
    request: Request,
    taskId: str,
    payload: dict[str, Any],
    if_match: str | None = Header(default=None, alias="If-Match"),
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    version = require_if_match(if_match)
    data = await _run(request, container.bids.update(actor, taskId, payload, if_match=version))
    return success(data, request=request)


@router.post("/bid-tasks/{taskId}/clone")
async def clone_bid_task(
    request: Request,
    taskId: str,
    payload: dict[str, Any],
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.bids.clone(actor, taskId, project_name=payload.get("projectName")))
    return success(data, request=request)


@router.post("/bid-tasks/{taskId}/archive")
async def archive_bid_task(
    request: Request,
    taskId: str,
    payload: dict[str, Any],
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.bids.archive(actor, taskId, reason=str(payload.get("reason") or "")))
    return success(data, request=request)


@router.post("/bid-tasks/{taskId}/assignments")
async def add_bid_assignment(
    request: Request,
    taskId: str,
    payload: dict[str, Any],
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, container.bids.add_assignment(actor, taskId, payload)), request=request)


@router.delete("/bid-tasks/{taskId}/assignments/{userId}", status_code=204)
async def remove_bid_assignment(
    request: Request,
    taskId: str,
    userId: str,
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    await _run(request, container.bids.remove_assignment(actor, taskId, userId))
    return Response(status_code=204, headers={"X-Request-Id": request_id(request)})


@router.put("/bid-tasks/{taskId}/tender-file")
async def set_bid_tender_file(
    request: Request,
    taskId: str,
    payload: dict[str, Any],
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, container.bids.set_tender_file(actor, taskId, payload)), request=request)


@router.post("/bid-tasks/{taskId}/parse", status_code=202)
async def parse_bid_tender(
    request: Request,
    taskId: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.bids.enqueue_parse(actor, taskId, idempotency_key=idempotency_key))
    return success(data, request=request, status_code=202)


@router.get("/bid-tasks/{taskId}/requirements")
async def get_bid_requirements(
    request: Request,
    taskId: str,
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, container.bids.get_requirements(actor, taskId)), request=request)


@router.patch("/bid-tasks/{taskId}/requirements")
async def update_bid_requirements(
    request: Request,
    taskId: str,
    payload: dict[str, Any],
    if_match: str | None = Header(default=None, alias="If-Match"),
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    version = require_if_match(if_match)
    data = await _run(request, container.bids.patch_requirements(actor, taskId, payload, if_match=version))
    return success(data, request=request)


@router.get("/bid-tasks/{taskId}/materials")
async def list_bid_materials(
    request: Request,
    taskId: str,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    category: str | None = None,
    status: str | None = None,
    required: bool | None = None,
    sortBy: str | None = None,
    sortOrder: str = "asc",
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data, meta = await _run(
        request,
        container.bids.list_materials(
            actor,
            taskId,
            page=page,
            page_size=pageSize,
            category=category,
            status=status,
            required=required,
            sort_by=sortBy,
            sort_order=sortOrder,
        ),
    )
    return success(data, request=request, meta=meta)


@router.post("/bid-tasks/{taskId}/materials")
async def create_bid_material(
    request: Request,
    taskId: str,
    payload: dict[str, Any],
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, container.bids.create_material(actor, taskId, payload)), request=request)


@router.patch("/bid-tasks/{taskId}/materials/{materialId}")
async def update_bid_material(
    request: Request,
    taskId: str,
    materialId: str,
    payload: dict[str, Any],
    if_match: str | None = Header(default=None, alias="If-Match"),
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    version = require_if_match(if_match)
    data = await _run(
        request,
        container.bids.update_material(actor, taskId, materialId, payload, if_match=version),
    )
    return success(data, request=request)


@router.delete("/bid-tasks/{taskId}/materials/{materialId}", status_code=204)
async def delete_bid_material(
    request: Request,
    taskId: str,
    materialId: str,
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    await _run(request, container.bids.delete_material(actor, taskId, materialId))
    return Response(status_code=204, headers={"X-Request-Id": request_id(request)})


@router.post("/bid-tasks/{taskId}/materials/match", status_code=202)
async def match_bid_materials(
    request: Request,
    taskId: str,
    payload: dict[str, Any] | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.bids.enqueue_material_match(
            actor,
            taskId,
            payload or {},
            idempotency_key=idempotency_key,
        ),
    )
    return success(data, request=request, status_code=202)


@router.put("/bid-tasks/{taskId}/materials/{materialId}/file")
async def bind_bid_material_file(
    request: Request,
    taskId: str,
    materialId: str,
    payload: dict[str, Any],
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.bids.bind_material_file(actor, taskId, materialId, payload))
    return success(data, request=request)


@router.delete("/bid-tasks/{taskId}/materials/{materialId}/file")
async def unbind_bid_material_file(
    request: Request,
    taskId: str,
    materialId: str,
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.bids.unbind_material_file(actor, taskId, materialId))
    return success(data, request=request)


@router.post("/bid-tasks/{taskId}/materials/batch-bind")
async def batch_bind_bid_materials(
    request: Request,
    taskId: str,
    payload: dict[str, Any],
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, container.bids.batch_bind(actor, taskId, payload)), request=request)


@router.get("/bid-tasks/{taskId}/materials/export")
async def export_bid_materials(
    request: Request,
    taskId: str,
    category: str | None = None,
    status: str | None = None,
    required: bool | None = None,
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    content = await _run(
        request,
        container.bids.export_materials(
            actor,
            taskId,
            category=category,
            status=status,
            required=required,
        ),
    )
    digest = sha256(content).hexdigest()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_binary_headers("bid-materials.xlsx", digest, request),
    )


@router.post("/bid-tasks/{taskId}/materials/templates", status_code=202)
async def generate_bid_material_templates(
    request: Request,
    taskId: str,
    payload: dict[str, Any],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.bids.enqueue_template_generate(
            actor,
            taskId,
            payload,
            idempotency_key=idempotency_key,
        ),
    )
    return success(data, request=request, status_code=202)


@router.post("/bid-tasks/{taskId}/reviews", status_code=202)
async def create_bid_review(
    request: Request,
    taskId: str,
    payload: dict[str, Any],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.bids.enqueue_review(actor, taskId, payload, idempotency_key=idempotency_key),
    )
    return success(data, request=request, status_code=202)


@router.get("/bid-tasks/{taskId}/reviews/latest")
async def latest_bid_review(
    request: Request,
    taskId: str,
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, container.bids.latest_review(actor, taskId)), request=request)


@router.post("/bid-tasks/{taskId}/review-findings/{findingId}/decision")
async def decide_bid_review_finding(
    request: Request,
    taskId: str,
    findingId: str,
    payload: dict[str, Any],
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.bids.decide_finding(actor, taskId, findingId, payload))
    return success(data, request=request)


@router.post("/bid-tasks/{taskId}/documents", status_code=202)
async def generate_bid_documents(
    request: Request,
    taskId: str,
    payload: dict[str, Any],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.bids.enqueue_document_generate(
            actor,
            taskId,
            payload,
            idempotency_key=idempotency_key,
        ),
    )
    return success(data, request=request, status_code=202)


@router.get("/bid-tasks/{taskId}/documents")
async def list_bid_documents(
    request: Request,
    taskId: str,
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    return success(await _run(request, container.bids.list_documents(actor, taskId)), request=request)


@router.get("/bid-tasks/{taskId}/documents/{documentId}/download")
async def download_bid_document(
    request: Request,
    taskId: str,
    documentId: str,
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    content, url, file_name, digest, mime_type = await _run(
        request,
        container.bids.download_document(actor, taskId, documentId),
    )
    headers = _binary_headers(file_name, digest, request)
    if content is not None:
        return Response(content=content, media_type=mime_type, headers=headers)
    return RedirectResponse(cast(str, url), status_code=307, headers=headers)


@router.get("/bid-tasks/{taskId}/document-versions")
async def list_bid_document_versions(
    request: Request,
    taskId: str,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data, meta = await _run(
        request,
        container.bids.list_document_versions(actor, taskId, page=page, page_size=pageSize),
    )
    return success(data, request=request, meta=meta)


@router.get("/bid-tasks/{taskId}/document-versions/compare")
async def compare_bid_document_versions(
    request: Request,
    taskId: str,
    fromVersionId: str,
    toVersionId: str,
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.bids.compare_document_versions(actor, taskId, fromVersionId, toVersionId),
    )
    return success(data, request=request)


@router.post("/bid-tasks/{taskId}/document-versions/{versionId}/rollback", status_code=202)
async def rollback_bid_document_version(
    request: Request,
    taskId: str,
    versionId: str,
    payload: dict[str, Any],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    container: M5BidsContainer = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.bids.enqueue_document_rollback(
            actor,
            taskId,
            versionId,
            payload,
            idempotency_key=idempotency_key,
        ),
    )
    return success(data, request=request, status_code=202)


def _binary_headers(file_name: str, digest: str, request: Request) -> dict[str, str]:
    safe_name = quote(file_name, safe="")
    return {
        "Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}",
        "X-File-Sha256": digest,
        "X-Request-Id": request_id(request),
    }


router.include_router(qualifications_router)
router.include_router(fragments_router)
