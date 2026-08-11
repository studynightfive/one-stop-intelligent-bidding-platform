"""Development seed and direct UI workflow transition coverage."""

from __future__ import annotations

import pytest

from app.domains.evaluations.container import build_m6_container
from app.domains.evaluations.demo_seed import DEMO_EVALUATION_ID, DEMO_PORTAL_INVITE_CODE
from app.domains.evaluations.ports import AuthPrincipal
from app.domains.evaluations.store import EvaluationStore


def _enable_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEMO_SEED_ENABLED", "true")


def test_demo_evaluation_seed_is_complete_and_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_demo(monkeypatch)
    store = EvaluationStore()
    evaluation = store.get_evaluation(
        DEMO_EVALUATION_ID,
        tenant_id="0190f4dd-0000-7000-8000-000000000002",
    )

    assert evaluation.status == "collecting"
    assert len(evaluation.materials) == 4
    assert len(evaluation.criteria) == 2
    assert len(evaluation.suppliers) == 3
    assert len(store.list_rounds(evaluation_id=DEMO_EVALUATION_ID)) == 1
    assert len(store.list_risks(evaluation_id=DEMO_EVALUATION_ID)) == 1

    from app.domains.evaluations.demo_seed import seed_demo_evaluation_store

    seed_demo_evaluation_store(store)
    assert len(store.evaluations) == 1
    assert len(store.rounds) == 1


@pytest.mark.asyncio
async def test_seeded_portal_entry_and_direct_ai_transition(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_demo(monkeypatch)
    container = build_m6_container()
    session = await container.portal.exchange(DEMO_PORTAL_INVITE_CODE)
    assert session["supplier"]["name"] == "深圳云启科技有限公司"

    actor = AuthPrincipal(
        user_id="0190f4dd-0000-7000-8000-000000000001",
        tenant_id="0190f4dd-0000-7000-8000-000000000002",
        name="演示管理员",
        role="admin",
    )
    await container.scoring.start_ai_scoring(actor, DEMO_EVALUATION_ID)
    evaluation = container.store.get_evaluation(DEMO_EVALUATION_ID, tenant_id=actor.tenant_id)
    assert evaluation.status == "ai_review"
    assert evaluation.current_step == 4
