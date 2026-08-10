"""M5 内部 RBAC 辅助（与 M6 access 风格一致；不依赖 M4）。"""

from __future__ import annotations

from app.domains.bids.entities import BidTaskEntity
from app.domains.bids.errors import forbidden
from app.domains.bids.ports import AuthPrincipal


def is_internal(actor: AuthPrincipal) -> bool:
    return actor.role in {"admin", "project_lead", "member", "reviewer"}


def require_internal(actor: AuthPrincipal) -> None:
    if not is_internal(actor):
        raise forbidden("需要内部用户身份")


def can_create(actor: AuthPrincipal) -> bool:
    return actor.role in {"admin", "project_lead"}


def require_create(actor: AuthPrincipal) -> None:
    if not can_create(actor):
        raise forbidden("仅管理员或项目负责人可创建投标任务")


def is_owner(actor: AuthPrincipal, task: BidTaskEntity) -> bool:
    if actor.role == "admin":
        return True
    if actor.role != "project_lead":
        return False
    if task.assignee_id == actor.user_id:
        return True
    for assignment in task.assignments:
        if assignment.user_id == actor.user_id and assignment.role_in_task == "owner":
            return True
    return False


def can_view(actor: AuthPrincipal, task: BidTaskEntity) -> bool:
    if actor.role == "admin":
        return True
    if not is_internal(actor):
        return False
    if task.assignee_id == actor.user_id:
        return True
    return any(assignment.user_id == actor.user_id for assignment in task.assignments)


def can_member_edit(actor: AuthPrincipal, task: BidTaskEntity) -> bool:
    """owner/member 角色：作为被分配的成员可写部分资源（材料/解析）。"""
    if actor.role == "admin":
        return True
    if actor.role not in {"project_lead", "member"}:
        return False
    if task.assignee_id == actor.user_id:
        return True
    return any(
        assignment.user_id == actor.user_id and assignment.role_in_task in {"owner", "collaborator"}
        for assignment in task.assignments
    )


def can_review(actor: AuthPrincipal, task: BidTaskEntity) -> bool:
    if actor.role == "admin":
        return True
    if actor.role == "reviewer":
        return (
            any(
                assignment.user_id == actor.user_id and assignment.role_in_task == "reviewer"
                for assignment in task.assignments
            )
            or task.assignee_id == actor.user_id
        )
    return actor.role == "project_lead" and task.assignee_id == actor.user_id


def require_owner(actor: AuthPrincipal, task: BidTaskEntity) -> None:
    if not is_owner(actor, task):
        raise forbidden("仅任务负责人或管理员可操作")


def require_viewer(actor: AuthPrincipal, task: BidTaskEntity) -> None:
    if not can_view(actor, task):
        raise forbidden("无权查看该投标任务")


def require_member_or_owner(actor: AuthPrincipal, task: BidTaskEntity) -> None:
    if not can_member_edit(actor, task):
        raise forbidden("仅任务成员、负责人或管理员可操作")


def require_reviewer(actor: AuthPrincipal, task: BidTaskEntity) -> None:
    if not can_review(actor, task):
        raise forbidden("仅评委、负责人或管理员可发起/处理审核")
