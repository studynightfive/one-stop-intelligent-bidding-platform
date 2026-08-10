"""ORM 模型可被中央 Base 元数据发现（L0 注册前的结构自检）。"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from app.domains.evaluations import models as evaluation_models
from app.domains.evaluations.repository import default_repository, evaluation_from_orm_row
from app.domains.evaluations.store import EvaluationStore
from app.models_registry import Base


def test_m6_tables_registered_on_import() -> None:
    table_names = set(Base.metadata.tables.keys())
    assert "evaluation_tasks" in table_names
    assert "evaluation_suppliers" in table_names
    assert "price_rounds" in table_names
    assert "score_items" in table_names
    assert "portal_sessions" in table_names
    assert evaluation_models.EvaluationTaskModel.__tablename__ == "evaluation_tasks"


def test_demo_repository_and_orm_row_mapping() -> None:
    now = datetime.now(UTC)
    row = SimpleNamespace(
        id="evaluation-1",
        tenant_id="tenant-1",
        source_bid_task_id=None,
        project_name="映射项目",
        tender_no="ZB-MAP",
        tender_entity="建设单位",
        budget_amount=Decimal("100.00"),
        currency="CNY",
        supplier_deadline=now + timedelta(days=1),
        evaluation_start_at=now + timedelta(days=2),
        evaluation_end_at=now + timedelta(days=3),
        status="draft",
        current_step=1,
        progress_percent=5,
        assignee_id="user-1",
        assignee_name="负责人",
        description=None,
        result_summary=None,
        review_settings={"multiRoundPricing": True, "maxRounds": 2},
        version=1,
        created_at=None,
        updated_at=None,
    )
    entity = evaluation_from_orm_row(row)
    assert entity.project_name == "映射项目"
    assert entity.review_settings.multi_round_pricing is True
    assert entity.review_settings.max_rounds == 2
    assert isinstance(default_repository(), EvaluationStore)
