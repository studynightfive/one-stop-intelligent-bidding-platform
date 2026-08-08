"""评标状态机测试。"""

import pytest

from app.domains.evaluations.errors import DomainError
from app.domains.evaluations.state_machine import assert_evaluation_transition, assert_supplier_transition


def test_evaluation_happy_path_transitions() -> None:
    assert_evaluation_transition("draft", "collecting")
    assert_evaluation_transition("collecting", "pending")
    assert_evaluation_transition("pending", "ai_review")
    assert_evaluation_transition("ai_review", "human_review")
    assert_evaluation_transition("human_review", "completed")
    assert_evaluation_transition("completed", "closed")


def test_illegal_evaluation_transition() -> None:
    with pytest.raises(DomainError) as exc:
        assert_evaluation_transition("draft", "closed")
    assert exc.value.code == "INVALID_STATE_TRANSITION"
    assert "currentStatus" in exc.value.details
    assert "allowedActions" in exc.value.details


def test_supplier_submit_path() -> None:
    assert_supplier_transition("invited", "partial")
    assert_supplier_transition("partial", "submitted")
    assert_supplier_transition("submitted", "supplementing")
    assert_supplier_transition("supplementing", "submitted")
