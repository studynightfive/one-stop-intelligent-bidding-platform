"""M5 fragments 领域的契约、权限、隔离与失败流测试。"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Literal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contracts.generated.models import Fragment, FragmentStats
from app.core.errors.handlers import register_exception_handlers
from app.domains.bids.entities import BidMaterialEntity, BidTaskEntity
from app.domains.bids.ports import AuthPrincipal, FileRefSnapshot, RecordingPorts, Role
from app.domains.bids.store import BidStore
from app.domains.fragments import (
    FragmentService,
    FragmentStore,
    SemanticSearchHit,
    SemanticSearchRequest,
    SemanticSearchResult,
)
from app.domains.fragments.router import get_actor, router


class FakeSemanticSearchPort:
    def __init__(self) -> None:
        self.calls: list[SemanticSearchRequest] = []
        self.result = SemanticSearchResult(hits=(), total=0)

    async def search(self, request: SemanticSearchRequest) -> SemanticSearchResult:
        self.calls.append(request)
        return SemanticSearchResult(
            hits=self.result.hits[request.offset : request.offset + request.limit],
            total=self.result.total,
        )


def _actor(
    *,
    user_id: str = "user-1",
    tenant_id: str = "tenant-1",
    role: Role = "project_lead",
) -> AuthPrincipal:
    return AuthPrincipal(user_id=user_id, tenant_id=tenant_id, name=user_id, role=role)


def _file(
    file_id: str = "file-clean",
    *,
    status: Literal["pending", "clean", "infected", "failed"] = "clean",
) -> FileRefSnapshot:
    return FileRefSnapshot(
        id=file_id,
        file_name=f"{file_id}.txt",
        mime_type="text/plain",
        size_bytes=128,
        sha256="a" * 64,
        scan_status=status,
        created_at=datetime.now(UTC),
    )


def _save_task(
    store: BidStore,
    *,
    task_id: str = "task-1",
    tenant_id: str = "tenant-1",
    assignee_id: str = "user-1",
) -> BidTaskEntity:
    now = datetime.now(UTC)
    return store.save_task(
        BidTaskEntity(
            id=task_id,
            tenant_id=tenant_id,
            project_name="Project",
            tender_no="T-1",
            tender_entity="Owner",
            deadline=now + timedelta(days=7),
            status="draft",
            current_step=1,
            progress_percent=5,
            assignee_id=assignee_id,
            assignee_name=assignee_id,
            created_at=now,
            updated_at=now,
        )
    )


@pytest.fixture
def context() -> SimpleNamespace:
    files_and_audit = RecordingPorts()
    files_and_audit.files["file-clean"] = _file()
    bid_store = BidStore()
    _save_task(bid_store)
    fragment_store = FragmentStore()
    semantic = FakeSemanticSearchPort()
    service = FragmentService(
        fragment_store,
        bid_store=bid_store,
        files=files_and_audit,
        audit=files_and_audit,
        semantic_search=semantic,
    )
    actor_box = {"actor": _actor()}
    app = FastAPI()
    register_exception_handlers(app)
    app.state.m5 = SimpleNamespace(fragments=service)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_actor] = lambda: actor_box["actor"]
    return SimpleNamespace(
        client=TestClient(app, raise_server_exceptions=False),
        service=service,
        fragment_store=fragment_store,
        bid_store=bid_store,
        ports=files_and_audit,
        semantic=semantic,
        actor_box=actor_box,
    )


def _create(client: TestClient, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Construction safety plan",
        "category": "technical",
        "summary": "Reusable safety language",
        "content": "Construction safety requirements and controls.",
        "documentVersion": "V1",
        "tags": ["construction", "safety"],
    }
    payload.update(overrides)
    response = client.post("/api/v1/fragments", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    Fragment.model_validate(data)
    return data


def test_router_exposes_exactly_nine_contract_operations() -> None:
    actual = {(method, route.path) for route in router.routes for method in route.methods or set()}
    assert actual == {
        ("GET", "/fragments/stats"),
        ("GET", "/fragments"),
        ("POST", "/fragments"),
        ("POST", "/fragments/semantic-search"),
        ("GET", "/fragments/{id}"),
        ("PATCH", "/fragments/{id}"),
        ("DELETE", "/fragments/{id}"),
        ("POST", "/fragments/{id}/versions"),
        ("POST", "/fragments/{id}/references"),
    }


def test_all_operations_and_camel_case_responses(context: SimpleNamespace) -> None:
    created = _create(context.client, sourceFileId="file-clean")
    fragment_id = str(created["id"])
    source_file = created["sourceFile"]
    assert isinstance(source_file, dict)
    assert source_file["scanStatus"] == "clean"

    stats = context.client.get("/api/v1/fragments/stats")
    assert stats.status_code == 200
    FragmentStats.model_validate(stats.json()["data"])
    assert stats.json()["data"] == {
        "total": 1,
        "categoryCount": 1,
        "totalReferences": 0,
        "semanticRecommended": 0,
    }
    listed = context.client.get("/api/v1/fragments")
    assert listed.status_code == 200
    assert listed.json()["meta"] == {"page": 1, "pageSize": 20, "total": 1, "totalPages": 1}
    assert context.client.get(f"/api/v1/fragments/{fragment_id}").status_code == 200

    updated = context.client.patch(
        f"/api/v1/fragments/{fragment_id}",
        headers={"If-Match": '"1"'},
        json={"summary": "Updated summary"},
    )
    assert updated.status_code == 200
    Fragment.model_validate(updated.json()["data"])
    assert updated.json()["data"]["version"] == 2

    context.semantic.result = SemanticSearchResult(
        hits=(
            SemanticSearchHit(
                fragment_id=fragment_id,
                match_score=1.0,
                match_reason="fake semantic match",
            ),
        ),
        total=1,
    )
    searched = context.client.post(
        "/api/v1/fragments/semantic-search",
        json={"query": "construction safety", "limit": 10},
    )
    assert searched.status_code == 200
    assert searched.json()["data"][0]["matchScore"] == 1.0

    versioned = context.client.post(
        f"/api/v1/fragments/{fragment_id}/versions",
        json={"content": "Version two", "changeNote": "Refresh wording"},
    )
    assert versioned.status_code == 200
    assert versioned.json()["data"]["version"] == 3

    referenced = context.client.post(
        f"/api/v1/fragments/{fragment_id}/references",
        json={"bidTaskId": "task-1"},
    )
    assert referenced.status_code == 200
    assert referenced.json()["data"] == {"referenced": True, "useCount": 1}

    context.actor_box["actor"] = _actor(user_id="admin", role="admin")
    deleted = context.client.request(
        "DELETE",
        f"/api/v1/fragments/{fragment_id}",
        json={"reason": "Retired"},
    )
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert context.client.get(f"/api/v1/fragments/{fragment_id}").status_code == 404
    assert len(context.ports.audits) == 5


def test_tenant_isolation_and_role_boundaries(context: SimpleNamespace) -> None:
    created = _create(context.client)
    fragment_id = str(created["id"])

    context.actor_box["actor"] = _actor(user_id="member", role="member")
    assert context.client.get(f"/api/v1/fragments/{fragment_id}").status_code == 200
    assert (
        context.client.post(
            "/api/v1/fragments",
            json={
                "title": "Denied",
                "category": "technical",
                "summary": "Denied",
                "content": "Denied",
                "documentVersion": "V1",
                "tags": [],
            },
        ).status_code
        == 403
    )
    assert (
        context.client.patch(
            f"/api/v1/fragments/{fragment_id}",
            headers={"If-Match": '"1"'},
            json={"summary": "Denied"},
        ).status_code
        == 403
    )

    context.actor_box["actor"] = _actor(tenant_id="tenant-2", user_id="other-admin", role="admin")
    assert context.client.get(f"/api/v1/fragments/{fragment_id}").status_code == 404
    assert context.client.get("/api/v1/fragments").json()["meta"]["total"] == 0

    context.actor_box["actor"] = _actor(role="project_lead")
    assert (
        context.client.request(
            "DELETE",
            f"/api/v1/fragments/{fragment_id}",
            json={"reason": "Denied"},
        ).status_code
        == 403
    )


def test_if_match_is_required_and_enforced(context: SimpleNamespace) -> None:
    fragment_id = str(_create(context.client)["id"])
    endpoint = f"/api/v1/fragments/{fragment_id}"
    assert context.client.patch(endpoint, json={"summary": "Missing"}).status_code == 422
    assert (
        context.client.patch(
            endpoint,
            headers={"If-Match": "1"},
            json={"summary": "Malformed"},
        ).status_code
        == 422
    )
    conflict = context.client.patch(
        endpoint,
        headers={"If-Match": '"99"'},
        json={"summary": "Stale"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "VERSION_CONFLICT"
    assert (
        context.client.patch(
            endpoint,
            headers={"If-Match": '"1"'},
            json={"summary": "Current"},
        ).status_code
        == 200
    )


def test_create_requires_content_or_clean_source_file(context: SimpleNamespace) -> None:
    missing = context.client.post(
        "/api/v1/fragments",
        json={
            "title": "Missing source",
            "category": "technical",
            "summary": "Missing source",
            "documentVersion": "V1",
            "tags": [],
        },
    )
    assert missing.status_code == 422

    for status in ("pending", "infected", "failed"):
        file_id = f"file-{status}"
        context.ports.files[file_id] = _file(file_id, status=status)
        rejected = context.client.post(
            "/api/v1/fragments",
            json={
                "title": "Rejected",
                "category": "technical",
                "summary": "Rejected",
                "sourceFileId": file_id,
                "documentVersion": "V1",
                "tags": [],
            },
        )
        assert rejected.status_code == 422
        assert rejected.json()["error"]["code"] == "FILE_REJECTED"

    assert (
        context.client.post(
            "/api/v1/fragments",
            json={
                "title": "Unknown file",
                "category": "technical",
                "summary": "Unknown file",
                "sourceFileId": "missing",
                "documentVersion": "V1",
                "tags": [],
            },
        ).status_code
        == 404
    )
    source_only = context.client.post(
        "/api/v1/fragments",
        json={
            "title": "Source only",
            "category": "technical",
            "summary": "Clean source file",
            "sourceFileId": "file-clean",
            "documentVersion": "V1",
            "tags": [],
        },
    )
    assert source_only.status_code == 201
    assert source_only.json()["data"]["sourceFile"]


def test_versions_and_references_preserve_ownership(context: SimpleNamespace) -> None:
    created = _create(context.client)
    fragment_id = str(created["id"])
    assert len(context.fragment_store.list_versions(tenant_id="tenant-1", fragment_id=fragment_id)) == 1

    versioned = context.client.post(
        f"/api/v1/fragments/{fragment_id}/versions",
        json={"content": "New body", "changeNote": "Second version"},
    )
    assert versioned.status_code == 200
    versions = context.fragment_store.list_versions(tenant_id="tenant-1", fragment_id=fragment_id)
    assert [version.version_number for version in versions] == [1, 2]
    assert versions[-1].change_note == "Second version"

    context.actor_box["actor"] = _actor(user_id="not-assigned")
    assert (
        context.client.post(
            f"/api/v1/fragments/{fragment_id}/references",
            json={"bidTaskId": "task-1"},
        ).status_code
        == 403
    )

    other_task = _save_task(context.bid_store, task_id="task-2")
    material = BidMaterialEntity(
        id="material-2",
        tenant_id="tenant-1",
        task_id=other_task.id,
        name="Material",
        category="technical",
        requirement="",
        required=True,
        sort_order=0,
    )
    context.bid_store.save_material(material)
    context.actor_box["actor"] = _actor()
    assert (
        context.client.post(
            f"/api/v1/fragments/{fragment_id}/references",
            json={"bidTaskId": "task-1", "materialId": material.id},
        ).status_code
        == 404
    )
    referenced = context.client.post(
        f"/api/v1/fragments/{fragment_id}/references",
        json={"bidTaskId": "task-1"},
    )
    assert referenced.status_code == 200
    records = context.fragment_store.list_references(tenant_id="tenant-1", fragment_id=fragment_id)
    assert len(records) == 1
    assert records[0].bid_task_id == "task-1"


def test_semantic_search_uses_tenant_scoped_port_and_maps_results(context: SimpleNamespace) -> None:
    first = _create(context.client)
    second = _create(
        context.client,
        title="Commercial payment terms",
        category="commercial",
        summary="Payment schedule",
        content="Construction payment schedule and invoicing.",
        tags=["payment"],
    )
    context.semantic.result = SemanticSearchResult(
        hits=(
            SemanticSearchHit(
                fragment_id=str(first["id"]),
                match_score=0.93,
                match_reason="fake semantic provider: safety meaning",
            ),
        ),
        total=1,
    )
    response = context.client.post(
        "/api/v1/fragments/semantic-search",
        json={"query": "construction safety", "category": "technical", "limit": 10},
    )
    assert response.status_code == 200
    semantic_results = response.json()["data"]
    assert semantic_results[0]["id"] == first["id"]
    assert semantic_results[0]["matchScore"] == 0.93
    assert semantic_results[0]["matchReason"] == "fake semantic provider: safety meaning"
    assert context.semantic.calls[-1] == SemanticSearchRequest(
        tenant_id="tenant-1",
        query="construction safety",
        category="technical",
        offset=0,
        limit=10,
    )

    context.semantic.result = SemanticSearchResult(
        hits=(
            SemanticSearchHit(
                fragment_id=str(first["id"]),
                match_score=0.93,
                match_reason="fake semantic provider: safety meaning",
            ),
            SemanticSearchHit(
                fragment_id=str(second["id"]),
                match_score=0.71,
                match_reason="fake semantic provider: commercial meaning",
            ),
        ),
        total=2,
    )
    before_calls = len(context.semantic.calls)
    semantic_list_response = context.client.get(
        "/api/v1/fragments",
        params={
            "page": 2,
            "pageSize": 1,
            "keyword": "construction safety",
            "searchMode": "semantic",
        },
    )
    assert semantic_list_response.status_code == 200
    assert len(context.semantic.calls) == before_calls + 1
    assert semantic_list_response.json()["data"][0]["id"] == second["id"]
    assert semantic_list_response.json()["meta"]["total"] == 2
    assert context.semantic.calls[-1] == SemanticSearchRequest(
        tenant_id="tenant-1",
        query="construction safety",
        category=None,
        offset=1,
        limit=1,
    )

    call_count = len(context.semantic.calls)
    keyword_list = context.client.get(
        "/api/v1/fragments",
        params={"keyword": "payment", "searchMode": "keyword"},
    ).json()["data"]
    assert [item["id"] for item in keyword_list] == [second["id"]]
    assert len(context.semantic.calls) == call_count


def test_semantic_page_shape_total_and_hits_are_strictly_validated(context: SimpleNamespace) -> None:
    own = _create(context.client)
    retired = _create(context.client, title="Retired fragment")
    context.semantic.result = SemanticSearchResult(
        hits=(
            SemanticSearchHit(
                fragment_id=str(own["id"]),
                match_score=0.9,
                match_reason="tenant-local result",
            ),
        ),
        total=999,
    )

    before_calls = len(context.semantic.calls)
    untrusted_total = context.client.get(
        "/api/v1/fragments",
        params={"keyword": "meaning", "searchMode": "semantic"},
    )
    assert untrusted_total.status_code == 503
    assert len(context.semantic.calls) == before_calls + 1

    context.semantic.result = SemanticSearchResult(
        hits=(
            SemanticSearchHit(
                fragment_id=str(own["id"]),
                match_score=0.9,
                match_reason="tenant-local result",
            ),
        ),
        total=1,
    )
    before_calls = len(context.semantic.calls)
    trusted = context.client.get(
        "/api/v1/fragments",
        params={"keyword": "meaning", "searchMode": "semantic"},
    )
    assert trusted.status_code == 200
    assert [item["id"] for item in trusted.json()["data"]] == [own["id"]]
    assert trusted.json()["meta"] == {"page": 1, "pageSize": 20, "total": 1, "totalPages": 1}
    assert len(context.semantic.calls) == before_calls + 1

    context.semantic.result = SemanticSearchResult(
        hits=(
            SemanticSearchHit(
                fragment_id=str(own["id"]),
                match_score=0.9,
                match_reason="incomplete first page",
            ),
        ),
        total=2,
    )
    before_calls = len(context.semantic.calls)
    incomplete_page = context.client.get(
        "/api/v1/fragments",
        params={"pageSize": 2, "keyword": "meaning", "searchMode": "semantic"},
    )
    assert incomplete_page.status_code == 503
    assert len(context.semantic.calls) == before_calls + 1

    context.actor_box["actor"] = _actor(tenant_id="tenant-2", user_id="tenant-2-lead")
    foreign = _create(context.client, title="Foreign fragment")
    context.actor_box["actor"] = _actor()
    context.semantic.result = SemanticSearchResult(
        hits=(
            SemanticSearchHit(
                fragment_id=str(foreign["id"]),
                match_score=0.8,
                match_reason="must not cross tenants",
            ),
        ),
        total=1,
    )

    rejected = context.client.get(
        "/api/v1/fragments",
        params={"keyword": "meaning", "searchMode": "semantic"},
    )
    assert rejected.status_code == 503
    assert rejected.json()["error"]["code"] == "SERVICE_UNAVAILABLE"

    context.semantic.result = SemanticSearchResult(
        hits=(
            SemanticSearchHit(
                fragment_id=str(own["id"]),
                match_score=0.9,
                match_reason="first copy",
            ),
            SemanticSearchHit(
                fragment_id=str(own["id"]),
                match_score=0.8,
                match_reason="duplicate copy",
            ),
        ),
        total=2,
    )
    duplicate = context.client.get(
        "/api/v1/fragments",
        params={"keyword": "meaning", "searchMode": "semantic"},
    )
    assert duplicate.status_code == 503

    context.actor_box["actor"] = _actor(user_id="admin", role="admin")
    deleted = context.client.request(
        "DELETE",
        f"/api/v1/fragments/{retired['id']}",
        json={"reason": "Retired"},
    )
    assert deleted.status_code == 204
    context.actor_box["actor"] = _actor()
    context.semantic.result = SemanticSearchResult(
        hits=(
            SemanticSearchHit(
                fragment_id=str(retired["id"]),
                match_score=0.7,
                match_reason="deleted result",
            ),
        ),
        total=1,
    )
    inactive = context.client.get(
        "/api/v1/fragments",
        params={"keyword": "meaning", "searchMode": "semantic"},
    )
    assert inactive.status_code == 503


def test_semantic_search_fails_closed_without_port(context: SimpleNamespace) -> None:
    _create(context.client)
    context.service.semantic_search_port = None

    endpoint = context.client.post(
        "/api/v1/fragments/semantic-search",
        json={"query": "safety meaning", "limit": 10},
    )
    assert endpoint.status_code == 503
    assert endpoint.json()["error"]["code"] == "SERVICE_UNAVAILABLE"

    semantic_list = context.client.get(
        "/api/v1/fragments",
        params={"keyword": "safety meaning", "searchMode": "semantic"},
    )
    assert semantic_list.status_code == 503
    assert semantic_list.json()["error"]["code"] == "SERVICE_UNAVAILABLE"

    keyword_list = context.client.get(
        "/api/v1/fragments",
        params={"keyword": "safety", "searchMode": "keyword"},
    )
    assert keyword_list.status_code == 200
    assert keyword_list.json()["meta"]["total"] == 1


def test_semantic_search_timeout_fails_closed_without_waiting(
    context: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HangingSemanticSearchPort:
        async def search(self, request: SemanticSearchRequest) -> SemanticSearchResult:
            del request
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

    _create(context.client)
    context.service.semantic_search_port = HangingSemanticSearchPort()
    monkeypatch.setattr("app.domains.fragments.service._SEMANTIC_SEARCH_TIMEOUT_SECONDS", 0.0)

    response = context.client.post(
        "/api/v1/fragments/semantic-search",
        json={"query": "timeout", "limit": 10},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_models_publish_three_migration_tables() -> None:
    from app.domains.fragments.models import FragmentModel, FragmentReferenceModel, FragmentVersionModel
    from app.models_registry import Base

    assert {"fragments", "fragment_versions", "fragment_references"} <= set(Base.metadata.tables)
    assert FragmentModel.__tablename__ == "fragments"
    assert FragmentVersionModel.__tablename__ == "fragment_versions"
    assert FragmentReferenceModel.__tablename__ == "fragment_references"
