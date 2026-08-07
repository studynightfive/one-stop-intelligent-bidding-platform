"""评分排名测试。"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domains.evaluations.container import build_m6_container
from app.domains.evaluations.entities import ScoreItemEntity
from app.domains.evaluations.ports import AuthPrincipal
from tests.evaluations.test_evaluation_service import _actor, _configured_evaluation


@pytest.mark.asyncio
async def test_ranking_uses_weighted_decimal() -> None:
    container = build_m6_container()
    actor = _actor()
    eid, _, criteria, suppliers = await _configured_evaluation(container, actor)
    await container.evaluations.publish(actor, eid, idempotency_key="pub-rank")
    # 手工写入分数
    container.store.save_score(
        ScoreItemEntity(
            evaluation_id=eid,
            supplier_id=suppliers[0]["id"],
            criterion_id=criteria[0]["id"],
            final_score=Decimal("100.00"),
        )
    )
    container.store.save_score(
        ScoreItemEntity(
            evaluation_id=eid,
            supplier_id=suppliers[0]["id"],
            criterion_id=criteria[1]["id"],
            final_score=Decimal("50.00"),
        )
    )
    container.store.save_score(
        ScoreItemEntity(
            evaluation_id=eid,
            supplier_id=suppliers[1]["id"],
            criterion_id=criteria[0]["id"],
            final_score=Decimal("80.00"),
        )
    )
    container.store.save_score(
        ScoreItemEntity(
            evaluation_id=eid,
            supplier_id=suppliers[1]["id"],
            criterion_id=criteria[1]["id"],
            final_score=Decimal("80.00"),
        )
    )
    ranking = await container.scoring.ranking(actor, eid)
    # A: 100*0.6 + 50*0.4 = 80; B: 80*0.6 + 80*0.4 = 80 — 同分按稳定排序
    assert ranking["rows"][0]["totalScore"] in {"80.00"}
    assert len(ranking["rows"]) == 2
