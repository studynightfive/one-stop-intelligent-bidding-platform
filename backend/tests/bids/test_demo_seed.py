"""Development demo seed coverage."""

from app.domains.bids.demo_seed import DEMO_TENANT_ID, GENERATION_READY_TASK_ID, seed_demo_bid_store
from app.domains.bids.store import BidStore


def test_demo_seed_is_disabled_in_test_environment(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEMO_SEED_ENABLED", "true")
    store = BidStore()
    assert store.tasks == {}


def test_demo_seed_creates_generation_ready_task_and_is_idempotent(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEMO_SEED_ENABLED", "true")
    store = BidStore()

    assert len(store.tasks) == 5
    task = store.get_task(GENERATION_READY_TASK_ID, tenant_id=DEMO_TENANT_ID)
    assert task.status == "ai_review"
    assert task.requirements is not None
    assert len(task.requirements.technical_requirements) == 4
    assert task.material_summary == {"total": 4, "have": 4, "missing": 0}
    assert task.latest_review is not None
    assert task.latest_review.status == "succeeded"

    seed_demo_bid_store(store)
    assert len(store.tasks) == 5
