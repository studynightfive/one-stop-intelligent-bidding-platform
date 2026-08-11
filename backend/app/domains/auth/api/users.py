"""User, role, and permission management HTTP routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from app.core.dependencies import AdminUser, AuthenticatedUser, DBSession
from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.core.http import pagination_meta, success_response
from app.domains.audit.mappers import audit_event_to_data
from app.domains.audit.services.audit_service import AuditService
from app.domains.auth.mappers import ROLE_PERMISSIONS, user_to_data
from app.domains.auth.models.user import UserRole, UserStatus
from app.domains.auth.schemas.auth import InviteUserRequest, UpdateUserRequest, UserStatusRequest
from app.domains.auth.services.auth_service import AuthService
from app.domains.auth.services.email_service import EmailService
from app.domains.auth.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["用户管理"])
metadata_router = APIRouter(tags=["用户管理"])


def _tenant_id(current_user: dict[str, Any]) -> UUID:
    return UUID(str(current_user["tenant_id"]))


def _actor_id(current_user: dict[str, Any]) -> UUID:
    return UUID(str(current_user["id"]))


def _ensure_self_or_admin(user_id: UUID, current_user: dict[str, Any]) -> None:
    if current_user.get("role") != "admin" and str(user_id) != str(current_user.get("id")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "只能查看自己的信息"},
        )


def _delivery_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": "EMAIL_DELIVERY_FAILED", "message": "邮件服务暂时不可用，请稍后重试"},
    )


@router.get("")
async def list_users(
    request: Request,
    current_user: AdminUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    sort_by: str = Query("createdAt", alias="sortBy", pattern="^(createdAt|name|email)$"),
    sort_order: str = Query("desc", alias="sortOrder", pattern="^(asc|desc)$"),
    keyword: str | None = Query(None, min_length=1),
    role: str | None = Query(None),
    department: str | None = Query(None),
    user_status: str | None = Query(None, alias="status"),
) -> JSONResponse:
    """Return a tenant-scoped, paginated user list."""
    try:
        role_enum = UserRole(role) if role else None
        status_enum = UserStatus(user_status) if user_status else None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "VALIDATION_ERROR", "message": "角色或用户状态无效"},
        ) from exc

    service = UserService(db)
    users, total = await service.list_users(
        tenant_id=_tenant_id(current_user),
        page=page,
        page_size=page_size,
        keyword=keyword,
        role=role_enum,
        department=department,
        status=status_enum,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return success_response(
        [user_to_data(user) for user in users],
        request=request,
        meta=pagination_meta(page=page, page_size=page_size, total=total),
    )


@router.post("/invitations", status_code=201)
async def invite_user(
    payload: InviteUserRequest,
    request: Request,
    current_user: AdminUser,
    db: DBSession,
) -> JSONResponse:
    """Create an invited account and deliver its activation link."""
    service = UserService(db)
    try:
        user = await service.create_user(
            tenant_id=_tenant_id(current_user),
            email=str(payload.email),
            name=payload.name,
            role=UserRole(payload.role),
            department=payload.department,
            phone=payload.phone,
            invited_by=_actor_id(current_user),
        )
    except (ValueError, ValidationError) as exc:
        message = exc.message if isinstance(exc, ValidationError) else "角色无效"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": message},
        ) from exc

    token, expires_at = service.create_invitation_token(user)
    delivered = await EmailService().send_invitation(email=user.email, name=user.name, token=token)
    if not delivered:
        # The account remains invited, allowing an administrator to resend when SMTP recovers.
        raise _delivery_unavailable()
    return success_response(
        {"user": user_to_data(user), "invitationExpiresAt": expires_at},
        request=request,
        status_code=201,
    )


@router.post("/{user_id}/invitations/resend")
async def resend_invitation(
    user_id: UUID,
    request: Request,
    current_user: AdminUser,
    db: DBSession,
) -> JSONResponse:
    """Issue and deliver a fresh invitation link."""
    service = UserService(db)
    try:
        user = await service.get_invited_user(user_id, _tenant_id(current_user))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code, "message": exc.message}) from exc
    token, _ = service.create_invitation_token(user)
    if not await EmailService().send_invitation(email=user.email, name=user.name, token=token):
        raise _delivery_unavailable()
    return success_response({"sent": True}, request=request)


@router.patch("/{user_id}")
async def update_user(
    user_id: UUID,
    payload: UpdateUserRequest,
    request: Request,
    current_user: AdminUser,
    db: DBSession,
    if_match: str = Header(..., alias="If-Match"),
) -> JSONResponse:
    """Update one user within the administrator's tenant."""
    if not if_match.strip():
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "If-Match 不能为空"})
    try:
        user = await UserService(db).update_user(
            user_id=user_id,
            name=payload.name,
            phone=payload.phone,
            department=payload.department,
            role=UserRole(payload.role) if payload.role else None,
            tenant_id=_tenant_id(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "角色无效"}) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code, "message": exc.message}) from exc
    return success_response(user_to_data(user), request=request)


@router.post("/{user_id}/status")
async def set_user_status(
    user_id: UUID,
    payload: UserStatusRequest,
    request: Request,
    current_user: AdminUser,
    db: DBSession,
) -> JSONResponse:
    """Enable or disable a tenant user with safety guards."""
    try:
        user = await UserService(db).set_user_status(
            user_id=user_id,
            status=UserStatus(payload.status),
            reason=payload.reason,
            tenant_id=_tenant_id(current_user),
            actor_id=_actor_id(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "用户状态无效"}) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code, "message": exc.message}) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code, "message": exc.message}) from exc
    return success_response(user_to_data(user), request=request)


@router.post("/{user_id}/password-reset-email")
async def send_password_reset_email(
    user_id: UUID,
    request: Request,
    current_user: AdminUser,
    db: DBSession,
) -> JSONResponse:
    """Deliver a password-reset link to a tenant user."""
    user = await UserService(db).get_user_by_id(user_id, tenant_id=_tenant_id(current_user))
    if user is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "用户不存在"})
    token = AuthService.create_password_reset_token(user)
    if not await EmailService().send_password_reset(email=user.email, name=user.name, token=token):
        raise _delivery_unavailable()
    return success_response({"sent": True}, request=request)


def _collect_user_projects(request: Request, *, tenant_id: str, user_id: str) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    bid_store = getattr(request.app.state, "m5_bid_store", None)
    if bid_store is not None:
        for task in bid_store.list_tasks(tenant_id=tenant_id, include_archived=True):
            assignment_ids = {assignment.user_id for assignment in task.assignments}
            if task.assignee_id != user_id and user_id not in assignment_ids:
                continue
            projects.append(
                {
                    "id": task.id,
                    "kind": "bid",
                    "title": task.project_name,
                    "code": task.tender_no,
                    "status": task.status,
                    "userRole": "负责人" if task.assignee_id == user_id else "协作成员",
                    "updatedAt": task.updated_at or task.created_at,
                }
            )

    evaluation_store = getattr(request.app.state, "m6_store", None)
    if evaluation_store is not None:
        for evaluation in evaluation_store.list_evaluations(tenant_id=tenant_id):
            if evaluation.assignee_id != user_id and user_id not in evaluation.reviewer_ids:
                continue
            projects.append(
                {
                    "id": evaluation.id,
                    "kind": "evaluation",
                    "title": evaluation.project_name,
                    "code": evaluation.tender_no,
                    "status": evaluation.status,
                    "userRole": "负责人" if evaluation.assignee_id == user_id else "评审员",
                    "updatedAt": evaluation.updated_at,
                }
            )
    return projects


@router.get("/{user_id}/projects")
async def get_user_projects(
    user_id: UUID,
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    sort_by: str = Query("updatedAt", alias="sortBy", pattern="^updatedAt$"),
    sort_order: str = Query("desc", alias="sortOrder", pattern="^(asc|desc)$"),
) -> JSONResponse:
    """Return projects assigned to the selected user."""
    _ensure_self_or_admin(user_id, current_user)
    tenant_id = _tenant_id(current_user)
    if await UserService(db).get_user_by_id(user_id, tenant_id=tenant_id) is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "用户不存在"})
    projects = _collect_user_projects(request, tenant_id=str(tenant_id), user_id=str(user_id))
    projects.sort(key=lambda item: item["updatedAt"], reverse=sort_order == "desc")
    start = (page - 1) * page_size
    data = projects[start : start + page_size]
    _ = sort_by
    return success_response(
        data,
        request=request,
        meta=pagination_meta(page=page, page_size=page_size, total=len(projects)),
    )


@router.get("/{user_id}/activity")
async def get_user_activity(
    user_id: UUID,
    request: Request,
    current_user: AuthenticatedUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    sort_by: str = Query("createdAt", alias="sortBy", pattern="^createdAt$"),
    sort_order: str = Query("desc", alias="sortOrder", pattern="^(asc|desc)$"),
    date_from: datetime | None = Query(None, alias="dateFrom"),
    date_to: datetime | None = Query(None, alias="dateTo"),
) -> JSONResponse:
    """Return real audit events generated by the selected user."""
    _ensure_self_or_admin(user_id, current_user)
    tenant_id = _tenant_id(current_user)
    if await UserService(db).get_user_by_id(user_id, tenant_id=tenant_id) is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "用户不存在"})
    events, total = await AuditService(db).list_events(
        tenant_id=tenant_id,
        actor_id=user_id,
        start_date=date_from,
        end_date=date_to,
        sort_order=sort_order,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    _ = sort_by
    return success_response(
        [audit_event_to_data(event) for event in events],
        request=request,
        meta=pagination_meta(page=page, page_size=page_size, total=total),
    )


ROLE_DEFINITIONS = [
    ("admin", "管理员", "系统管理员，拥有所有权限"),
    ("project_lead", "项目负责人", "负责投标项目管理、生成与评审"),
    ("reviewer", "评审员", "参与标书与供应商评审"),
    ("member", "成员", "查看并参与获分配的项目"),
]


@metadata_router.get("/roles")
async def list_roles(request: Request, current_user: AdminUser, db: DBSession) -> JSONResponse:
    """Return role definitions with live tenant user counts."""
    counts = await UserService(db).count_users_by_role(_tenant_id(current_user))
    data = [
        {
            "role": role,
            "label": label,
            "description": description,
            "permissions": ROLE_PERMISSIONS[role],
            "userCount": counts.get(UserRole(role), 0),
        }
        for role, label, description in ROLE_DEFINITIONS
    ]
    return success_response(data, request=request)


PERMISSION_MATRIX = {
    "users": {
        "read": ["admin", "project_lead"],
        "write": ["admin"],
        "delete": ["admin"],
    },
    "projects": {
        "read": ["admin", "project_lead", "reviewer", "member"],
        "write": ["admin", "project_lead"],
        "delete": ["admin"],
    },
    "bids": {
        "read": ["admin", "project_lead", "reviewer", "member"],
        "write": ["admin", "project_lead"],
        "review": ["admin", "project_lead", "reviewer"],
    },
    "settings": {"read": ["admin"], "write": ["admin"]},
    "audit": {"read": ["admin"], "export": ["admin"]},
    "files": {
        "upload": ["admin", "project_lead", "reviewer", "member"],
        "download": ["admin", "project_lead", "reviewer", "member"],
        "delete": ["admin"],
    },
}


@metadata_router.get("/permissions/matrix")
async def get_permissions_matrix(request: Request, current_user: AdminUser) -> JSONResponse:
    """Return the contract-shaped role/action matrix."""
    _ = current_user
    return success_response(
        {"modules": [{"module": module, "actions": actions} for module, actions in PERMISSION_MATRIX.items()]},
        request=request,
    )
