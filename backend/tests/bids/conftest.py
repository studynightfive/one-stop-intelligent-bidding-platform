"""Focused M5 HTTP harness without changing the central application router."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors.handlers import register_exception_handlers
from app.domains.bids.container import M5BidsContainer, build_m5_bids_container
from app.domains.bids.ports import AuthPrincipal, FileRefSnapshot
from app.domains.bids.router import get_actor
from app.domains.bids.router import router as bids_router


@dataclass
class BidHttpHarness:
    client: TestClient
    container: M5BidsContainer
    actors: dict[str, AuthPrincipal]

    @property
    def actor(self) -> AuthPrincipal:
        return self.actors["current"]

    @actor.setter
    def actor(self, value: AuthPrincipal) -> None:
        self.actors["current"] = value

    def add_file(
        self,
        file_id: str,
        *,
        file_name: str = "tender.pdf",
        mime_type: str = "application/pdf",
        content: bytes = b"test-file",
    ) -> FileRefSnapshot:
        assert self.container.ports is not None
        from hashlib import sha256

        file_ref = FileRefSnapshot(
            id=file_id,
            file_name=file_name,
            mime_type=mime_type,
            size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
            scan_status="clean",
            created_at=datetime.now(UTC),
        )
        self.container.ports.files[file_id] = file_ref
        return file_ref

    def create_task(self, project_name: str = "M5 HTTP 项目") -> dict[str, object]:
        file_id = f"tender-{len(self.container.store.tasks) + 1}"
        self.add_file(file_id)
        response = self.client.post(
            "/api/v1/bid-tasks",
            json={
                "projectName": project_name,
                "tenderNo": f"NO-{len(self.container.store.tasks) + 1}",
                "tenderEntity": "建设单位",
                "deadline": (datetime.now(UTC) + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
                "assigneeId": self.actor.user_id,
                "tenderFileId": file_id,
                "tags": ["m5"],
            },
        )
        assert response.status_code == 201, response.text
        return response.json()["data"]


@pytest.fixture
def bid_http() -> Iterator[BidHttpHarness]:
    container = build_m5_bids_container()
    actors = {
        "current": AuthPrincipal(
            user_id="user-owner",
            tenant_id="tenant-a",
            name="负责人",
            role="admin",
        )
    }
    app = FastAPI()
    register_exception_handlers(app)
    app.state.m5 = container
    app.include_router(bids_router, prefix="/api/v1")
    app.dependency_overrides[get_actor] = lambda: actors["current"]
    with TestClient(app) as client:
        yield BidHttpHarness(client=client, container=container, actors=actors)
