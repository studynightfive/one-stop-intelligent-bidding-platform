"""评标内部 API 路由（§8.4）。由 L0 在中央 Router include。

依赖注入约定：应用启动时设置 `app.state.m6 = build_m6_container(...)`，
并由 M4 提供 `get_auth_principal`；测试可覆盖。
"""

from __future__ import annotations

from collections.abc import Awaitable, Mapping
from typing import Any, TypeVar, cast

from fastapi import APIRouter, Depends, Header, Request, Response

from app.domains.evaluations.container import M6Container
from app.domains.evaluations.errors import DomainError
from app.domains.evaluations.http import domain_http_exception, parse_if_match, success
from app.domains.evaluations.ports import AuthPrincipal, Role

router = APIRouter(tags=["evaluations"])
_T = TypeVar("_T")


def get_container(request: Request) -> M6Container:
    container = getattr(request.app.state, "m6", None)
    if container is None:
        raise RuntimeError("M6 container 未装配：请由 L0/集成层注入 app.state.m6")
    return cast(M6Container, container)


def auth_principal_from_context(current_user: Mapping[str, Any]) -> AuthPrincipal:
    """Map M4's authenticated user context to M6's stable service principal."""
    user_id = current_user.get("id")
    tenant_id = current_user.get("tenant_id")
    if not user_id or not tenant_id:
        raise DomainError(code="UNAUTHENTICATED", message="认证上下文缺少用户或租户标识")
    raw_role = str(current_user.get("role", "member"))
    role = raw_role if raw_role in {"admin", "project_lead", "member", "reviewer"} else "member"
    permissions = tuple(str(item) for item in current_user.get("permissions", ()))
    return AuthPrincipal(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        name=str(current_user.get("name") or current_user.get("email") or "用户"),
        role=cast(Role, role),
        permissions=permissions,
    )


def get_actor(request: Request) -> AuthPrincipal:
    """Read the principal injected by the L0/M4 integration dependency."""
    actor = getattr(request.state, "auth_principal", None)
    if not isinstance(actor, AuthPrincipal):
        raise domain_http_exception(
            DomainError(code="UNAUTHENTICATED", message="未认证"),
            request=request,
        )
    return actor


async def _run(request: Request, coro: Awaitable[_T]) -> _T:
    try:
        return await coro
    except DomainError as exc:
        raise domain_http_exception(exc, request=request) from exc


@router.get("/evaluations/stats")
async def evaluations_stats(
    request: Request,
    keyword: str | None = None,
    status: str | None = None,
    assigneeId: str | None = None,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request, container.evaluations.stats(actor, keyword=keyword, status=status, assignee_id=assigneeId)
    )
    return success(data, request=request)


@router.get("/evaluations")
async def list_evaluations(
    request: Request,
    page: int = 1,
    pageSize: int = 20,
    keyword: str | None = None,
    status: str | None = None,
    assigneeId: str | None = None,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data, meta = await _run(
        request,
        container.evaluations.list_tasks(
            actor, page=page, page_size=pageSize, keyword=keyword, status=status, assignee_id=assigneeId
        ),
    )
    return success(data, request=request, meta=meta)


@router.post("/evaluations", status_code=201)
async def create_evaluation(
    request: Request,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.evaluations.create_draft(actor, payload))
    return success(data, request=request, status_code=201)


@router.post("/evaluations/from-bid-task/{bidTaskId}")
async def create_from_bid(
    request: Request,
    bidTaskId: str,
    payload: dict[str, Any] | None = None,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    copy_materials = True if payload is None else bool(payload.get("copyMaterials", True))
    data = await _run(
        request, container.evaluations.create_from_bid_task(actor, bidTaskId, copy_materials=copy_materials)
    )
    return success(data, request=request, status_code=201)


@router.get("/evaluations/{evaluationId}")
async def get_evaluation(
    request: Request,
    evaluationId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.evaluations.get_detail(actor, evaluationId))
    return success(data, request=request)


@router.patch("/evaluations/{evaluationId}")
async def patch_evaluation(
    request: Request,
    evaluationId: str,
    payload: dict[str, Any],
    if_match: str | None = Header(default=None, alias="If-Match"),
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.evaluations.update(actor, evaluationId, payload, if_match=parse_if_match(if_match)),
    )
    return success(data, request=request)


@router.put("/evaluations/{evaluationId}/materials")
async def put_materials(
    request: Request,
    evaluationId: str,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.evaluations.put_materials(actor, evaluationId, payload.get("items", [])))
    return success(data, request=request)


@router.put("/evaluations/{evaluationId}/criteria")
async def put_criteria(
    request: Request,
    evaluationId: str,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.evaluations.put_criteria(actor, evaluationId, payload.get("items", [])))
    return success(data, request=request)


@router.put("/evaluations/{evaluationId}/review-settings")
async def put_review_settings(
    request: Request,
    evaluationId: str,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.evaluations.put_review_settings(actor, evaluationId, payload))
    return success(data, request=request)


@router.put("/evaluations/{evaluationId}/reviewers")
async def put_reviewers(
    request: Request,
    evaluationId: str,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.evaluations.put_reviewers(actor, evaluationId, payload.get("reviewerIds", [])))
    return success(data, request=request)


@router.put("/evaluations/{evaluationId}/suppliers")
async def put_suppliers(
    request: Request,
    evaluationId: str,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.evaluations.put_suppliers(actor, evaluationId, payload.get("items", [])))
    return success(data, request=request)


@router.post("/evaluations/{evaluationId}/validate")
async def validate_evaluation(
    request: Request,
    evaluationId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.evaluations.validate(actor, evaluationId))
    return success(data, request=request)


@router.get("/evaluations/{evaluationId}/preview")
async def preview_evaluation(
    request: Request,
    evaluationId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.evaluations.preview(actor, evaluationId))
    return success(data, request=request)


@router.post("/evaluations/{evaluationId}/publish")
async def publish_evaluation(
    request: Request,
    evaluationId: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.evaluations.publish(actor, evaluationId, idempotency_key=idempotency_key))
    return success(data, request=request)


@router.post("/evaluations/{evaluationId}/cancel")
async def cancel_evaluation(
    request: Request,
    evaluationId: str,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.evaluations.cancel(actor, evaluationId, str(payload.get("reason", ""))))
    return success(data, request=request)


@router.get("/evaluations/{evaluationId}/suppliers")
async def list_suppliers(
    request: Request,
    evaluationId: str,
    page: int = 1,
    pageSize: int = 20,
    status: str | None = None,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data, meta = await _run(
        request, container.evaluations.list_suppliers(actor, evaluationId, page=page, page_size=pageSize, status=status)
    )
    return success(data, request=request, meta=meta)


@router.get("/evaluations/{evaluationId}/suppliers/{supplierId}/submissions")
async def list_submissions(
    request: Request,
    evaluationId: str,
    supplierId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    from app.domains.evaluations.mappers import submission_dict

    try:
        entity = container.store.get_evaluation(evaluationId, tenant_id=actor.tenant_id)
        _ = entity
        items = container.store.list_submissions(evaluation_id=evaluationId, supplier_id=supplierId)
        data = []
        for item in items:
            file_obj = await container.scoring.files.get_file(tenant_id=actor.tenant_id, file_id=item.file_id)
            data.append(submission_dict(item, file_obj))
        return success(data, request=request)
    except DomainError as exc:
        raise domain_http_exception(exc, request=request) from exc


@router.get("/evaluations/{evaluationId}/supplier-invites")
async def list_invites(
    request: Request,
    evaluationId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.evaluations.list_invites(actor, evaluationId))
    return success(data, request=request)


@router.post("/evaluations/{evaluationId}/supplier-invites/{supplierId}/rotate")
async def rotate_invite(
    request: Request,
    evaluationId: str,
    supplierId: str,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.evaluations.rotate_invite(actor, evaluationId, supplierId, str(payload.get("reason", ""))),
    )
    return success(data, request=request)


@router.post("/evaluations/{evaluationId}/supplier-invites/{supplierId}/revoke")
async def revoke_invite(
    request: Request,
    evaluationId: str,
    supplierId: str,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.evaluations.revoke_invite(actor, evaluationId, supplierId, str(payload.get("reason", ""))),
    )
    return success(data, request=request)


@router.post("/evaluations/{evaluationId}/supplement-notices")
async def create_notice(
    request: Request,
    evaluationId: str,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.pricing.create_supplement_notice(actor, evaluationId, payload))
    return success(data, request=request, status_code=201)


@router.get("/evaluations/{evaluationId}/supplement-notices")
async def list_notices(
    request: Request,
    evaluationId: str,
    page: int = 1,
    pageSize: int = 20,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data, meta = await _run(request, container.pricing.list_notices(actor, evaluationId, page=page, page_size=pageSize))
    return success(data, request=request, meta=meta)


@router.post("/evaluations/{evaluationId}/price-rounds")
async def create_price_round(
    request: Request,
    evaluationId: str,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.pricing.create_round(actor, evaluationId, payload))
    return success(data, request=request, status_code=201)


@router.get("/evaluations/{evaluationId}/price-rounds")
async def list_price_rounds(
    request: Request,
    evaluationId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.pricing.list_rounds(actor, evaluationId))
    return success(data, request=request)


@router.post("/evaluations/{evaluationId}/price-rounds/{roundId}/close")
async def close_price_round(
    request: Request,
    evaluationId: str,
    roundId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.pricing.close_round(actor, evaluationId, roundId))
    return success(data, request=request)


@router.get("/evaluations/{evaluationId}/price-comparison")
async def price_comparison(
    request: Request,
    evaluationId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.pricing.comparison(actor, evaluationId))
    return success(data, request=request)


@router.post("/evaluations/{evaluationId}/material-checks")
async def material_checks(
    request: Request,
    evaluationId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.scoring.start_material_check(actor, evaluationId))
    return success(data, request=request, status_code=202)


@router.get("/evaluations/{evaluationId}/material-checks/latest")
async def latest_material_check(
    request: Request,
    evaluationId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.scoring.latest_material_check(actor, evaluationId))
    return success(data, request=request)


@router.post("/evaluations/{evaluationId}/risk-checks")
async def risk_checks(
    request: Request,
    evaluationId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.scoring.start_risk_check(actor, evaluationId))
    return success(data, request=request, status_code=202)


@router.get("/evaluations/{evaluationId}/risks")
async def list_risks(
    request: Request,
    evaluationId: str,
    severity: str | None = None,
    decision: str | None = None,
    supplierId: str | None = None,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.scoring.list_risks(actor, evaluationId, severity=severity, decision=decision, supplier_id=supplierId),
    )
    return success(data, request=request)


@router.post("/evaluations/{evaluationId}/risks/{riskId}/decision")
async def decide_risk(
    request: Request,
    evaluationId: str,
    riskId: str,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.scoring.decide_risk(
            actor,
            evaluationId,
            riskId,
            decision=str(payload.get("decision", "")),
            reason=str(payload.get("reason", "")),
        ),
    )
    return success(data, request=request)


@router.post("/evaluations/{evaluationId}/ai-scoring")
async def ai_scoring(
    request: Request,
    evaluationId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.scoring.start_ai_scoring(actor, evaluationId))
    return success(data, request=request, status_code=202)


@router.get("/evaluations/{evaluationId}/scores")
async def list_scores(
    request: Request,
    evaluationId: str,
    supplierId: str | None = None,
    category: str | None = None,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request, container.scoring.list_scores(actor, evaluationId, supplier_id=supplierId, category=category)
    )
    return success(data, request=request)


@router.patch("/evaluations/{evaluationId}/scores/{supplierId}/{criterionId}")
async def patch_score(
    request: Request,
    evaluationId: str,
    supplierId: str,
    criterionId: str,
    payload: dict[str, Any],
    if_match: str | None = Header(default=None, alias="If-Match"),
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.scoring.adjust_score(
            actor,
            evaluationId,
            supplierId,
            criterionId,
            human_score=str(payload.get("humanScore", "")),
            adjustment_reason=str(payload.get("adjustmentReason", "")),
            if_match=parse_if_match(if_match),
        ),
    )
    return success(data, request=request)


@router.post("/evaluations/{evaluationId}/scores/confirm")
async def confirm_scores(
    request: Request,
    evaluationId: str,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    supplier_id = payload.get("supplierId")
    data = await _run(
        request,
        container.scoring.confirm_scores(
            actor,
            evaluationId,
            supplier_id=str(supplier_id) if supplier_id else None,
            comment=payload.get("comment"),
        ),
    )
    return success(data, request=request)


@router.get("/evaluations/{evaluationId}/ranking")
async def ranking(
    request: Request,
    evaluationId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.scoring.ranking(actor, evaluationId))
    return success(data, request=request)


@router.post("/evaluations/{evaluationId}/reports")
async def create_report(
    request: Request,
    evaluationId: str,
    payload: dict[str, Any],
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    formats = payload.get("formats") or ["docx", "pdf"]
    data = await _run(request, container.scoring.start_report(actor, evaluationId, list(formats)))
    return success(data, request=request, status_code=202)


@router.get("/evaluations/{evaluationId}/reports")
async def list_reports(
    request: Request,
    evaluationId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(request, container.scoring.list_reports(actor, evaluationId))
    return success(data, request=request)


@router.get("/evaluations/{evaluationId}/reports/{reportId}/download")
async def download_report(
    request: Request,
    evaluationId: str,
    reportId: str,
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    from app.domains.evaluations.binary import binary_file_response, binary_redirect
    from app.domains.evaluations.pdf_util import build_simple_pdf

    try:
        report = container.store.get_report(reportId)
        if report.evaluation_id != evaluationId:
            raise DomainError(code="NOT_FOUND", message="报告不存在")
        _ = container.store.get_evaluation(evaluationId, tenant_id=actor.tenant_id)
        file_obj = await container.scoring.files.get_file(tenant_id=actor.tenant_id, file_id=report.file_id)
        if file_obj.download_url:
            return binary_redirect(file_obj.download_url, sha256=file_obj.sha256)
        # 无签名 URL 时回退为可打开的占位 Binary（集成后由 MinIO 真文件替代）
        pdf = build_simple_pdf(
            [
                "Evaluation Report",
                f"ReportId: {report.id}",
                f"Format: {report.format}",
                f"FileId: {file_obj.id}",
            ]
        )
        ext = "pdf" if report.format == "pdf" else "pdf"
        return binary_file_response(
            content=pdf,
            file_name=f"evaluation-report-{report.id[:8]}.{ext}",
            content_type="application/pdf",
            sha256=file_obj.sha256 if len(file_obj.sha256) == 64 else None,
        )
    except DomainError as exc:
        raise domain_http_exception(exc, request=request) from exc


@router.post("/evaluations/{evaluationId}/close")
async def close_evaluation(
    request: Request,
    evaluationId: str,
    payload: dict[str, Any],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    container: M6Container = Depends(get_container),
    actor: AuthPrincipal = Depends(get_actor),
) -> Response:
    data = await _run(
        request,
        container.evaluations.close(
            actor, evaluationId, str(payload.get("resultSummary", "")), idempotency_key=idempotency_key
        ),
    )
    return success(data, request=request)
