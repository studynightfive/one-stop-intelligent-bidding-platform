"""M5 投标任务状态机（§9.1）。"""

from __future__ import annotations

from app.domains.bids.errors import invalid_transition

# §9.1 状态机
TRANSITIONS: dict[str, set[str]] = {
    "draft": {"parsing", "failed"},
    "parsing": {"material_prep", "failed"},
    "material_prep": {"ai_review", "failed"},
    "ai_review": {"pending_output", "failed"},
    "pending_output": {"completed", "failed"},
    "completed": {"archived"},
    "archived": set(),
    "failed": {"parsing", "material_prep", "ai_review", "pending_output"},
}

# 状态 -> 允许动作（用于 409 details.allowedActions）
ACTIONS: dict[str, list[str]] = {
    "draft": [
        "update",
        "upload_tender",
        "assign",
        "parse",
        "configure_requirements",
        "configure_materials",
    ],
    "parsing": ["view", "assign", "upload_tender"],
    "material_prep": ["view", "assign", "match_materials", "upload_material", "template"],
    "ai_review": ["view", "assign", "review", "decide_finding"],
    "pending_output": ["view", "assign", "generate_document", "rollback_document"],
    "completed": ["view", "archive", "report_download"],
    "archived": ["view"],
    "failed": ["retry", "view"],
}

# 状态 -> (current_step, progress_percent)
PROGRESS: dict[str, tuple[int, int]] = {
    "draft": (1, 5),
    "parsing": (2, 20),
    "material_prep": (3, 40),
    "ai_review": (4, 60),
    "pending_output": (5, 80),
    "completed": (6, 95),
    "archived": (7, 100),
    "failed": (1, 0),
}


def step_for(status: str) -> int:
    return PROGRESS.get(status, (1, 0))[0]


def progress_for(status: str) -> int:
    return PROGRESS.get(status, (1, 0))[1]


def assert_transition(current: str, target: str) -> None:
    allowed = TRANSITIONS.get(current, set())
    if target not in allowed:
        raise invalid_transition(current, ACTIONS.get(current, []))
