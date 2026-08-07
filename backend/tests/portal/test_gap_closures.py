"""未完成项补强：截止、关闭只读、Refresh Cookie、回执 Binary。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domains.evaluations.container import build_m6_container
from app.domains.evaluations.errors import DomainError
from app.domains.evaluations.ids import new_id
from app.domains.evaluations.ports import AuthPrincipal, FileRefSnapshot, PortalPrincipal
from app.domains.evaluations.router import router as evaluations_router
from app.domains.portal.router import router as portal_router
from app.domains.portal.service import PORTAL_REFRESH_COOKIE
from tests.evaluations.test_evaluation_service import _actor, _configured_evaluation


@pytest.mark.asyncio
async def test_deadline_blocks_portal_upload() -> None:
    container = build_m6_container()
    actor = _actor()
    eid, materials, _, _ = await _configured_evaluation(container, actor)
    published = await container.evaluations.publish(actor, eid, idempotency_key="pub-dl")
    invite = published["invites"][0]["inviteUrl"].rsplit("/", 1)[-1]
    session = await container.portal.exchange(invite)
    principal = container.portal.resolve_principal(session["portalAccessToken"])

    entity = container.store.get_evaluation(eid, tenant_id=actor.tenant_id)
    entity.supplier_deadline = datetime.now(UTC) - timedelta(hours=1)
    container.store.save_evaluation(entity)

    with pytest.raises(DomainError) as exc:
        await container.portal.put_material_file(principal, materials[0]["id"], new_id())
    assert exc.value.code == "DEADLINE_PASSED"


@pytest.mark.asyncio
async def test_closed_blocks_quote_and_upload() -> None:
    container = build_m6_container()
    actor = _actor()
    reviewer = AuthPrincipal(user_id="u-reviewer-1", tenant_id="t-1", name="评委", role="reviewer")
    eid, materials, criteria, suppliers = await _configured_evaluation(container, actor)
    await container.evaluations.publish(actor, eid, idempotency_key="pub-close")
    await container.scoring.advance_to_pending(actor, eid)
    await container.scoring.start_ai_scoring(reviewer, eid)
    await container.scoring.adjust_score(
        reviewer,
        eid,
        suppliers[0]["id"],
        criteria[0]["id"],
        human_score="90.00",
        adjustment_reason="优秀",
        if_match=1,
    )
    await container.scoring.confirm_scores(reviewer, eid, supplier_id=None, comment="ok")
    await container.evaluations.close(actor, eid, "完成", idempotency_key="close-x")

    portal = PortalPrincipal(
        supplier_id=suppliers[0]["id"], evaluation_id=eid, tenant_id="t-1", name="甲"
    )
    with pytest.raises(DomainError) as exc:
        await container.portal.put_material_file(portal, materials[0]["id"], new_id())
    assert exc.value.code in {"CONFLICT", "DEADLINE_PASSED", "FORBIDDEN"}


@pytest.mark.asyncio
async def test_refresh_cookie_and_receipt_binary() -> None:
    container = build_m6_container()
    assert container.ports is not None
    actor = _actor()
    eid, materials, _, _ = await _configured_evaluation(container, actor)
    published = await container.evaluations.publish(actor, eid, idempotency_key="pub-bin")
    invite = published["invites"][0]["inviteUrl"].rsplit("/", 1)[-1]

    app = FastAPI()
    app.state.m6 = container
    app.include_router(evaluations_router, prefix="/api/v1")
    app.include_router(portal_router, prefix="/api/v1")
    client = TestClient(app)

    exchange = client.post("/api/v1/portal/session/exchange", json={"inviteCode": invite})
    assert exchange.status_code == 200
    assert PORTAL_REFRESH_COOKIE in exchange.cookies
    access = exchange.json()["data"]["portalAccessToken"]

    refreshed = client.post("/api/v1/portal/session/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["data"]["portalAccessToken"] != access

    file_id = new_id()
    container.ports.files[file_id] = FileRefSnapshot(
        id=file_id,
        file_name="a.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        sha256="b" * 64,
        scan_status="clean",
        created_at=datetime.now(UTC),
    )
    principal = container.portal.resolve_principal(refreshed.json()["data"]["portalAccessToken"])
    await container.portal.put_material_file(principal, materials[0]["id"], file_id)
    await container.portal.submit(principal, confirmed=True, idempotency_key="sub-bin")

    receipt = client.get(
        "/api/v1/portal/receipt",
        headers={"Authorization": f"Bearer {refreshed.json()['data']['portalAccessToken']}"},
    )
    assert receipt.status_code == 200
    assert receipt.headers["content-type"].startswith("application/pdf")
    assert "X-File-Sha256" in receipt.headers
    assert receipt.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_illegal_publish_from_collecting() -> None:
    container = build_m6_container()
    actor = _actor()
    eid, _, _, _ = await _configured_evaluation(container, actor)
    await container.evaluations.publish(actor, eid, idempotency_key="pub-once")
    with pytest.raises(DomainError) as exc:
        await container.evaluations.publish(actor, eid, idempotency_key="pub-twice-new")
    assert exc.value.code == "INVALID_STATE_TRANSITION"
