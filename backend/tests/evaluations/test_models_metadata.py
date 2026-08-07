"""ORM 模型可被中央 Base 元数据发现（L0 注册前的结构自检）。"""

from app.domains.evaluations import models as evaluation_models
from app.models_registry import Base


def test_m6_tables_registered_on_import() -> None:
    table_names = set(Base.metadata.tables.keys())
    assert "evaluation_tasks" in table_names
    assert "evaluation_suppliers" in table_names
    assert "price_rounds" in table_names
    assert "score_items" in table_names
    assert "portal_sessions" in table_names
    assert evaluation_models.EvaluationTaskModel.__tablename__ == "evaluation_tasks"
