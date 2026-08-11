"""Cross-module search over the application's live domain stores."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.core.dependencies import AuthenticatedUser, DBSession
from app.core.http import success_response

router = APIRouter(prefix="/global-search", tags=["全局搜索"])

PAGES = [
    ("dashboard", "投标工作台", "投标任务、进度与待办", "/dashboard"),
    ("evaluation", "评标工作台", "供应商、评分与定标", "/evaluation"),
    ("qualification", "资质库管理", "企业证照与到期提醒", "/admin/qualifications"),
    ("fragment", "文档片段库", "常用技术与商务内容", "/admin/fragments"),
    ("users", "用户与权限", "成员、角色与权限矩阵", "/admin/users"),
    ("settings", "系统设置", "模型、文档与通知配置", "/admin/settings"),
]


def _score(keyword: str, title: str, subtitle: str = "") -> float:
    query = keyword.casefold().strip()
    normalized_title = title.casefold()
    normalized_subtitle = subtitle.casefold()
    if normalized_title == query:
        return 1.0
    if normalized_title.startswith(query):
        return 0.92
    if query in normalized_title:
        return 0.82
    if query in normalized_subtitle:
        return 0.62
    return 0.0


def _append_result(
    results: list[dict[str, Any]],
    *,
    keyword: str,
    result_type: str,
    result_id: str,
    title: str,
    subtitle: str,
    route: str,
) -> None:
    score = _score(keyword, title, subtitle)
    if score <= 0:
        return
    results.append(
        {
            "type": result_type,
            "id": result_id,
            "title": title,
            "subtitle": subtitle,
            "route": route,
            "score": score,
        }
    )


@router.get("")
async def global_search(
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
    keyword: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    """Search pages, bids, evaluations, qualifications, and fragments."""
    tenant_id = str(current_user["tenant_id"])
    user_id = str(current_user["id"])
    privileged = current_user.get("role") in {"admin", "project_lead"}
    results: list[dict[str, Any]] = []

    for page_id, title, subtitle, route in PAGES:
        if current_user.get("role") != "admin" and page_id in {"users", "settings"}:
            continue
        _append_result(
            results,
            keyword=keyword,
            result_type="page",
            result_id=page_id,
            title=title,
            subtitle=subtitle,
            route=route,
        )

    bid_store = getattr(request.app.state, "m5_bid_store", None)
    if bid_store is not None:
        for task in bid_store.list_tasks(tenant_id=tenant_id, include_archived=True):
            assigned = task.assignee_id == user_id or any(item.user_id == user_id for item in task.assignments)
            if not privileged and not assigned:
                continue
            _append_result(
                results,
                keyword=keyword,
                result_type="bidTask",
                result_id=task.id,
                title=task.project_name,
                subtitle=f"{task.tender_no} · {task.tender_entity}",
                route=f"/tasks/{task.id}",
            )

    evaluation_store = getattr(request.app.state, "m6_store", None)
    if evaluation_store is not None:
        for evaluation in evaluation_store.list_evaluations(tenant_id=tenant_id):
            assigned = evaluation.assignee_id == user_id or user_id in evaluation.reviewer_ids
            if not privileged and not assigned:
                continue
            _append_result(
                results,
                keyword=keyword,
                result_type="evaluation",
                result_id=evaluation.id,
                title=evaluation.project_name,
                subtitle=f"{evaluation.tender_no} · {evaluation.tender_entity}",
                route=f"/evaluation/{evaluation.id}",
            )

    qualification_store = getattr(request.app.state, "m5_qualification_store", None)
    if qualification_store is not None:
        for qualification in qualification_store.list(tenant_id=tenant_id):
            _append_result(
                results,
                keyword=keyword,
                result_type="qualification",
                result_id=qualification.id,
                title=qualification.name,
                subtitle=f"{qualification.category} · {qualification.cert_number}",
                route=f"/admin/qualifications?selected={qualification.id}",
            )

    fragment_store = getattr(request.app.state, "m5_fragment_store", None)
    if fragment_store is not None:
        for fragment in fragment_store.list_active(tenant_id=tenant_id):
            _append_result(
                results,
                keyword=keyword,
                result_type="fragment",
                result_id=fragment.id,
                title=fragment.title,
                subtitle=f"{fragment.category} · {fragment.summary}",
                route=f"/admin/fragments?selected={fragment.id}",
            )

    _ = db
    results.sort(key=lambda item: (-float(item["score"]), str(item["title"])))
    return success_response(results[:limit], request=request)
