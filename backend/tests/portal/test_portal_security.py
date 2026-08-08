"""门户安全与会话测试。"""

from __future__ import annotations

import pytest

from app.domains.evaluations.container import build_m6_container
from app.domains.evaluations.errors import DomainError
from app.domains.portal.security import generate_invite_code, hash_secret
from tests.evaluations.test_evaluation_service import _actor, _configured_evaluation


def test_invite_code_hashed() -> None:
    raw, digest, masked = generate_invite_code()
    assert digest == hash_secret(raw)
    assert "****" in masked
    assert raw not in masked


@pytest.mark.asyncio
async def test_revoke_blocks_exchange() -> None:
    container = build_m6_container()
    actor = _actor()
    eid, _, _, suppliers = await _configured_evaluation(container, actor)
    published = await container.evaluations.publish(actor, eid, idempotency_key="pub-rev")
    invite = published["invites"][0]["inviteUrl"].rsplit("/", 1)[-1]
    await container.evaluations.revoke_invite(actor, eid, suppliers[0]["id"], "测试撤销")
    with pytest.raises(DomainError) as exc:
        await container.portal.exchange(invite)
    assert exc.value.code == "FORBIDDEN"
