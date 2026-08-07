"""报价领域测试。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domains.evaluations.container import build_m6_container
from app.domains.evaluations.errors import DomainError
from app.domains.evaluations.ports import AuthPrincipal, PortalPrincipal
from tests.evaluations.test_evaluation_service import _configured_evaluation, _actor


@pytest.mark.asyncio
async def test_quote_deadline_and_money() -> None:
    container = build_m6_container()
    actor = _actor()
    eid, _, _, suppliers = await _configured_evaluation(container, actor)
    await container.evaluations.publish(actor, eid, idempotency_key="pub-price")
    now = datetime.now(UTC)
    round_data = await container.pricing.create_round(
        actor,
        eid,
        {
            "title": "第二轮报价",
            "opensAt": (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            "deadline": (now + timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
            "eligibleSupplierIds": [suppliers[0]["id"]],
            "rankingVisibleToSupplier": True,
        },
    )
    portal = PortalPrincipal(
        supplier_id=suppliers[0]["id"],
        evaluation_id=eid,
        tenant_id="t-1",
        name="甲供应商",
    )
    with pytest.raises(DomainError):
        await container.pricing.submit_quote(portal, round_data["id"], amount="10.1", currency="CNY", idempotency_key=None)
    quote = await container.pricing.submit_quote(
        portal, round_data["id"], amount="999999.99", currency="CNY", idempotency_key="q-1"
    )
    again = await container.pricing.submit_quote(
        portal, round_data["id"], amount="999999.99", currency="CNY", idempotency_key="q-1"
    )
    assert quote == again
    # 非资格供应商
    other = PortalPrincipal(
        supplier_id=suppliers[1]["id"], evaluation_id=eid, tenant_id="t-1", name="乙"
    )
    with pytest.raises(DomainError) as exc:
        await container.pricing.submit_quote(other, round_data["id"], amount="1.00", currency="CNY", idempotency_key="q-2")
    assert exc.value.code == "FORBIDDEN"
