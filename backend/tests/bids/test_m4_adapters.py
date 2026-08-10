"""M5 integration adapters for the shared M4 job service and M6 snapshot port."""

from __future__ import annotations

import asyncio
import inspect
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from sys import modules
from types import ModuleType, SimpleNamespace
from uuid import UUID

import pytest

from app.domains.bids.container import build_m5_bids_container_with_m4
from app.domains.bids.entities import BidMaterialEntity, BidTaskEntity, TenderRequirementsEntity
from app.domains.bids.m4_adapters import M5BidTaskSnapshotAdapter, M5JobDispatcherAdapter, build_m4_ports
from app.domains.bids.store import BidStore


class _FakeDispatcher:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def dispatch(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(
            id=UUID("00000000-0000-0000-0000-000000000099"),
            status="queued",
            progress_percent=0,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            current_step=None,
        )


class _FakeJobType(StrEnum):
    AI_ANALYSIS = "ai_analysis"
    DOCUMENT_GENERATION = "document_generation"
    FILE_IMPORT = "file_import"
    EXPORT = "export"


def test_m4_assembly_requires_an_explicit_authorized_file_port() -> None:
    adapter_parameter = inspect.signature(build_m4_ports).parameters["files"]
    container_parameter = inspect.signature(build_m5_bids_container_with_m4).parameters["files"]

    assert adapter_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert adapter_parameter.default is inspect.Parameter.empty
    assert container_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert container_parameter.default is inspect.Parameter.empty

    with pytest.raises(TypeError, match="authorized FileServicePort"):
        build_m4_ports(object(), files=object())  # type: ignore[arg-type]


def test_m5_job_types_map_to_m4_without_falling_back_to_other(monkeypatch: pytest.MonkeyPatch) -> None:
    job_module = ModuleType("app.domains.jobs.models.job")
    job_module.JobType = _FakeJobType  # type: ignore[attr-defined]
    monkeypatch.setitem(modules, "app.domains.jobs.models.job", job_module)

    dispatcher = _FakeDispatcher()
    adapter = M5JobDispatcherAdapter(dispatcher)
    expected = {
        "ai_analysis": "ai_analysis",
        "document_generation": "document_generation",
        "file_import": "file_import",
        "export": "export",
    }

    for index, (job_type, m4_value) in enumerate(expected.items()):
        result = asyncio.run(
            adapter.enqueue(
                tenant_id="00000000-0000-0000-0000-000000000001",
                job_type=job_type,
                payload={"index": index},
                created_by="00000000-0000-0000-0000-000000000002",
                project_id="00000000-0000-0000-0000-000000000003",
                idempotency_key=f"key-{index}",
            )
        )
        call = dispatcher.calls[index]
        assert call["job_type"] == _FakeJobType(m4_value)
        assert call["input_data"] == {"index": index, "idempotencyKey": f"key-{index}"}
        assert result.type == job_type
        assert result.status == "queued"

    with pytest.raises(ValueError, match="Unsupported M5 job type"):
        asyncio.run(
            adapter.enqueue(
                tenant_id="00000000-0000-0000-0000-000000000001",
                job_type="unknown",
                payload={},
                created_by="00000000-0000-0000-0000-000000000002",
            )
        )


def test_m6_snapshot_is_tenant_scoped_and_contains_bid_materials() -> None:
    store = BidStore()
    deadline = datetime(2027, 5, 1, tzinfo=UTC)
    store.save_task(
        BidTaskEntity(
            id="task-1",
            tenant_id="tenant-a",
            project_name="Project Alpha",
            tender_no="TN-001",
            tender_entity="Buyer",
            deadline=deadline,
            status="material_prep",
            current_step=2,
            progress_percent=35,
            assignee_id="owner-1",
            assignee_name="Owner",
        )
    )
    store.save_requirements(
        "task-1",
        TenderRequirementsEntity(
            tenant_id="tenant-a",
            task_id="task-1",
            project_info={"budgetAmount": "100000.50"},
            scoring_items=[{"name": "Technical", "score": "60"}],
        ),
    )
    store.save_material(
        BidMaterialEntity(
            id="material-1",
            tenant_id="tenant-a",
            task_id="task-1",
            name="Technical proposal",
            category="technical",
            requirement="Complete response",
            required=True,
            sort_order=1,
        )
    )

    adapter = M5BidTaskSnapshotAdapter(store)
    snapshot = asyncio.run(adapter.get_snapshot(tenant_id="tenant-a", bid_task_id="task-1"))

    assert snapshot.tenant_id == "tenant-a"
    assert snapshot.deadline == deadline
    assert snapshot.budget_amount == Decimal("100000.50")
    assert snapshot.materials[0].name == "Technical proposal"
    assert snapshot.materials[0].category == "technical"
    assert snapshot.scoring_hints == ({"name": "Technical", "score": "60"},)

    with pytest.raises(KeyError):
        asyncio.run(adapter.get_snapshot(tenant_id="tenant-b", bid_task_id="task-1"))
