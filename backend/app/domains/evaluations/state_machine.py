"""评标与供应商状态机（后端唯一裁决）。"""

from __future__ import annotations

from app.domains.evaluations.errors import invalid_transition

EVALUATION_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"collecting", "cancelled"},
    "collecting": {"pending", "cancelled"},
    "pending": {"ai_review"},
    "ai_review": {"human_review"},
    "human_review": {"completed"},
    "completed": {"closed", "human_review"},  # human_review 仅管理员复开
    "closed": set(),
    "cancelled": set(),
}

SUPPLIER_TRANSITIONS: dict[str, set[str]] = {
    "invited": {"partial", "overdue", "withdrawn", "submitted"},
    "partial": {"submitted", "overdue", "withdrawn"},
    "submitted": {"supplementing", "qualified", "disqualified", "withdrawn"},
    "supplementing": {"submitted"},
    "qualified": set(),
    "disqualified": set(),
    "overdue": set(),
    "withdrawn": set(),
}

# 状态 -> 允许动作（用于 409 details.allowedActions）
EVALUATION_ACTIONS: dict[str, list[str]] = {
    "draft": ["update", "configure", "validate", "preview", "publish", "cancel"],
    "collecting": ["view", "supplement", "price_round", "cancel", "advance_pending"],
    "pending": ["material_check", "risk_check", "start_ai_scoring"],
    "ai_review": ["view_scores", "start_human_review"],
    "human_review": ["adjust_score", "confirm_scores", "decide_risk", "complete", "ranking", "report"],
    "completed": ["ranking", "report", "close", "reopen"],
    "closed": ["view", "audit_export"],
    "cancelled": ["view"],
}


def assert_evaluation_transition(current: str, target: str, *, admin_reopen: bool = False) -> None:
    allowed = EVALUATION_TRANSITIONS.get(current, set())
    if target == "human_review" and current == "completed" and not admin_reopen:
        raise invalid_transition(current, EVALUATION_ACTIONS.get(current, []))
    if target not in allowed:
        raise invalid_transition(current, EVALUATION_ACTIONS.get(current, []))


def assert_supplier_transition(current: str, target: str) -> None:
    allowed = SUPPLIER_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise invalid_transition(current, sorted(allowed))


def evaluation_step_for(status: str) -> int:
    mapping = {
        "draft": 1,
        "collecting": 2,
        "pending": 3,
        "ai_review": 4,
        "human_review": 5,
        "completed": 6,
        "closed": 6,
        "cancelled": 1,
    }
    return mapping.get(status, 1)


def evaluation_progress_for(status: str) -> int:
    mapping = {
        "draft": 5,
        "collecting": 25,
        "pending": 40,
        "ai_review": 60,
        "human_review": 80,
        "completed": 95,
        "closed": 100,
        "cancelled": 0,
    }
    return mapping.get(status, 0)
