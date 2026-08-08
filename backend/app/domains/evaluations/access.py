"""M6 内部 RBAC 辅助（路由层仍依赖 M4 AuthContext 注入）。"""

from __future__ import annotations

from app.domains.evaluations.entities import EvaluationEntity
from app.domains.evaluations.errors import forbidden
from app.domains.evaluations.ports import AuthPrincipal


def require_internal(actor: AuthPrincipal) -> None:
    if actor.role not in {"admin", "project_lead", "member", "reviewer"}:
        raise forbidden("需要内部用户身份")


def can_create(actor: AuthPrincipal) -> bool:
    return actor.role in {"admin", "project_lead"}


def can_own(actor: AuthPrincipal, entity: EvaluationEntity) -> bool:
    return actor.role == "admin" or entity.assignee_id == actor.user_id


def can_review(actor: AuthPrincipal, entity: EvaluationEntity) -> bool:
    if actor.role == "admin":
        return True
    if actor.role == "reviewer" and actor.user_id in entity.reviewer_ids:
        return True
    return actor.role == "project_lead" and entity.assignee_id == actor.user_id


def can_view(actor: AuthPrincipal, entity: EvaluationEntity) -> bool:
    if actor.role == "admin":
        return True
    if entity.assignee_id == actor.user_id:
        return True
    if actor.user_id in entity.reviewer_ids:
        return True
    # member 只读已分配任务；此处简化为同租户可见，最终以 M4 资源 ACL 为准
    return actor.role in {"project_lead", "member", "reviewer"}


def require_create(actor: AuthPrincipal) -> None:
    if not can_create(actor):
        raise forbidden("仅管理员或项目负责人可创建评标")


def require_owner(actor: AuthPrincipal, entity: EvaluationEntity) -> None:
    if not can_own(actor, entity):
        raise forbidden("仅任务负责人或管理员可操作")


def require_viewer(actor: AuthPrincipal, entity: EvaluationEntity) -> None:
    if not can_view(actor, entity):
        raise forbidden("无权查看该评标任务")


def require_reviewer(actor: AuthPrincipal, entity: EvaluationEntity) -> None:
    if not can_review(actor, entity):
        raise forbidden("仅评委、负责人或管理员可评分/复核")
