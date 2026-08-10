"""资质库 10 个 OpenAPI operation 及关键领域门禁。"""

from __future__ import annotations

import asyncio
import zipfile
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contracts.generated.models import JobRef, Qualification, QualificationStats
from app.core.errors.handlers import register_exception_handlers
from app.domains.bids.container import M5BidsContainer, build_m5_bids_container
from app.domains.bids.errors import DomainError
from app.domains.bids.ports import AuthPrincipal, FileRefSnapshot
from app.domains.qualifications.router import get_actor
from app.domains.qualifications.router import router as qualifications_router


def _actor(*, role: str = "admin", tenant_id: str = "tenant-a", user_id: str = "user-a") -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id,
        tenant_id=tenant_id,
        name="测试用户",
        role=role,  # type: ignore[arg-type]
    )


def _file(file_id: str, *, scan_status: str = "clean") -> FileRefSnapshot:
    return FileRefSnapshot(
        id=file_id,
        file_name=f"{file_id}.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256=sha256(file_id.encode()).hexdigest(),
        scan_status=scan_status,  # type: ignore[arg-type]
        created_at=datetime.now(UTC),
        preview_url=f"https://files.example.test/{file_id}/preview",
    )


def _client(actor: AuthPrincipal, container: M5BidsContainer | None = None) -> tuple[TestClient, M5BidsContainer]:
    resolved = container or build_m5_bids_container()
    app = FastAPI()
    register_exception_handlers(app)
    app.state.m5 = resolved
    app.include_router(qualifications_router, prefix="/api/v1")
    app.dependency_overrides[get_actor] = lambda: actor
    return TestClient(app), resolved


def _payload(
    *,
    file_id: str,
    cert_number: str,
    expiry_date: date | None = None,
    reminder_days: list[int] | None = None,
    valid_from: date | None = None,
) -> dict[str, object]:
    return {
        "name": f"资质-{cert_number}",
        "category": "企业资质",
        "certNumber": cert_number,
        "issuer": "测试发证机构",
        "validFrom": (valid_from or date.today()).isoformat(),
        "expiryDate": expiry_date.isoformat() if expiry_date else None,
        "fileId": file_id,
        "documentVersion": "1.0",
        "reminderDays": reminder_days if reminder_days is not None else [30, 60, 90],
        "tags": ["投标", "测试"],
    }


def _data(response, expected_status: int = 200):
    assert response.status_code == expected_status, response.text
    body = response.json()
    assert body["success"] is True
    assert body["requestId"]
    return body["data"]


def _import_row(cert_number: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "name": f"导入资质-{cert_number}",
        "category": "企业资质",
        "certNumber": cert_number,
        "issuer": "导入发证机构",
        "validFrom": "2026-01-01",
        "expiryDate": "2027-01-01",
        "documentVersion": "1.0",
        "reminderDays": [30, 60],
        "tags": ["导入"],
    }
    row.update(overrides)
    return row


def test_all_ten_http_operations_and_binary_outputs() -> None:
    client, container = _client(_actor())
    assert container.ports is not None
    captured_enqueue = AsyncMock(wraps=container.ports.enqueue)
    container.qualifications.jobs = SimpleNamespace(enqueue=captured_enqueue)  # type: ignore[assignment]
    for file_id in ("qualification-v1", "qualification-v2", "qualification-import"):
        container.ports.files[file_id] = _file(file_id)
    container.ports.download_urls["qualification-v2"] = "https://files.example.test/signed/qualification-v2"

    QualificationStats.model_validate(_data(client.get("/api/v1/qualifications/stats")))
    created = _data(
        client.post(
            "/api/v1/qualifications",
            json=_payload(
                file_id="qualification-v1",
                cert_number="CERT-001",
                expiry_date=date.today() + timedelta(days=365),
                reminder_days=[30],
            ),
        ),
        201,
    )
    Qualification.model_validate(created)
    qualification_id = created["id"]
    assert len(container.qualification_store.versions) == 1

    listed = _data(client.get("/api/v1/qualifications", params={"keyword": "CERT-001"}))
    assert [item["id"] for item in listed] == [qualification_id]
    assert _data(client.get(f"/api/v1/qualifications/{qualification_id}"))["id"] == qualification_id

    updated = _data(
        client.patch(
            f"/api/v1/qualifications/{qualification_id}",
            headers={"If-Match": '"1"'},
            json={"issuer": "更新后的发证机构"},
        )
    )
    assert updated["version"] == 2
    assert updated["issuer"] == "更新后的发证机构"

    versioned = _data(
        client.post(
            f"/api/v1/qualifications/{qualification_id}/versions",
            json={
                "fileId": "qualification-v2",
                "documentVersion": "2.0",
                "changeNote": "年度更新",
            },
        )
    )
    assert versioned["version"] == 3
    assert versioned["file"]["id"] == "qualification-v2"
    assert len(container.qualification_store.versions) == 2

    first_import = _data(
        client.post(
            "/api/v1/qualifications/imports",
            json={"fileId": "qualification-import"},
        ),
        202,
    )
    second_import = _data(
        client.post(
            "/api/v1/qualifications/imports",
            json={"fileId": "qualification-import"},
        ),
        202,
    )
    JobRef.model_validate(first_import)
    assert first_import == second_import
    assert len(container.ports.jobs) == 1
    first_job_call = captured_enqueue.await_args_list[0].kwargs
    assert first_job_call["job_type"] == "file_import"
    assert first_job_call["payload"]["m5JobType"] == "qualification.import"
    other_client, _ = _client(_actor(tenant_id="tenant-b", user_id="other-admin"), container)
    other_tenant_import = _data(
        other_client.post(
            "/api/v1/qualifications/imports",
            json={"fileId": "qualification-import"},
        ),
        202,
    )
    assert other_tenant_import["id"] != first_import["id"]
    assert len(container.ports.jobs) == 2

    template = client.get("/api/v1/qualifications/import-template")
    assert template.status_code == 200
    assert template.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert template.headers["x-file-sha256"] == sha256(template.content).hexdigest()
    with zipfile.ZipFile(BytesIO(template.content)) as workbook:
        assert "xl/workbook.xml" in workbook.namelist()
        assert "xl/worksheets/sheet1.xml" in workbook.namelist()

    download = client.get(f"/api/v1/qualifications/{qualification_id}/download", follow_redirects=False)
    assert download.status_code == 307
    assert download.headers["location"].endswith("/signed/qualification-v2")
    assert download.headers["x-file-sha256"] == _file("qualification-v2").sha256

    assert (
        client.request(
            "DELETE",
            f"/api/v1/qualifications/{qualification_id}",
            json={"reason": "已失效"},
        ).status_code
        == 204
    )
    stored = container.qualification_store.qualifications[qualification_id]
    assert stored.deleted_at is not None
    assert stored.deleted_reason == "已失效"
    assert client.get(f"/api/v1/qualifications/{qualification_id}").status_code == 404
    assert _data(client.get("/api/v1/qualifications/stats"))["total"] == 0
    assert [event.action for event in container.ports.audits if event.tenant_id == "tenant-a"] == [
        "qualification.created",
        "qualification.updated",
        "qualification.version_added",
        "qualification.import_requested",
        "qualification.deleted",
    ]


def test_dynamic_status_filters_tenant_isolation_and_rbac() -> None:
    admin = _actor()
    client, container = _client(admin)
    assert container.ports is not None
    expiries = {
        "valid-file": date.today() + timedelta(days=365),
        "expiring-file": date.today() + timedelta(days=10),
        "expired-file": date.today() - timedelta(days=1),
    }
    for index, (file_id, expiry) in enumerate(expiries.items(), start=1):
        container.ports.files[file_id] = _file(file_id)
        _data(
            client.post(
                "/api/v1/qualifications",
                json=_payload(
                    file_id=file_id,
                    cert_number=f"DYNAMIC-{index}",
                    expiry_date=expiry,
                    reminder_days=[30],
                    valid_from=(date.today() - timedelta(days=365) if expiry < date.today() else date.today()),
                ),
            ),
            201,
        )

    assert _data(client.get("/api/v1/qualifications/stats")) == {
        "total": 3,
        "valid": 1,
        "expiring": 1,
        "expired": 1,
    }
    assert len(container.ports.notifications) == 2
    expiring = _data(client.get("/api/v1/qualifications", params={"status": "expiring"}))
    assert len(expiring) == 1
    assert expiring[0]["certNumber"] == "DYNAMIC-2"
    assert len(_data(client.get("/api/v1/qualifications", params={"expiresWithinDays": 30}))) == 1
    qualification_id = expiring[0]["id"]

    other_client, _ = _client(_actor(tenant_id="tenant-b", user_id="other-admin"), container)
    assert other_client.get(f"/api/v1/qualifications/{qualification_id}").status_code == 404

    member_client, _ = _client(_actor(role="member", user_id="member-a"), container)
    assert member_client.get("/api/v1/qualifications").status_code == 200
    assert (
        member_client.post(
            "/api/v1/qualifications",
            json=_payload(file_id="valid-file", cert_number="NO-WRITE"),
        ).status_code
        == 403
    )

    lead_client, _ = _client(_actor(role="project_lead", user_id="lead-a"), container)
    assert (
        lead_client.post(
            "/api/v1/qualifications",
            json=_payload(file_id="valid-file", cert_number="LEAD-CREATE"),
        ).status_code
        == 201
    )
    assert (
        lead_client.request(
            "DELETE",
            f"/api/v1/qualifications/{qualification_id}",
            json={"reason": "无权删除"},
        ).status_code
        == 403
    )


def test_if_match_clean_file_and_request_shape_guards() -> None:
    client, container = _client(_actor())
    assert container.ports is not None
    container.ports.files["clean"] = _file("clean")
    container.ports.files["infected"] = _file("infected", scan_status="infected")

    rejected = client.post(
        "/api/v1/qualifications",
        json=_payload(file_id="infected", cert_number="INFECTED"),
    )
    assert rejected.status_code == 422
    assert container.qualification_store.qualifications == {}

    created = _data(
        client.post(
            "/api/v1/qualifications",
            json=_payload(file_id="clean", cert_number="CLEAN"),
        ),
        201,
    )
    qualification_id = created["id"]
    assert client.patch(f"/api/v1/qualifications/{qualification_id}", json={"issuer": "缺少版本"}).status_code == 422
    assert (
        client.patch(
            f"/api/v1/qualifications/{qualification_id}",
            headers={"If-Match": '"99"'},
            json={"issuer": "过期版本"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/qualifications/imports",
            json={"fileId": "clean", "unexpected": True},
        ).status_code
        == 422
    )
    assert (
        client.request(
            "DELETE",
            f"/api/v1/qualifications/{qualification_id}",
            json={"reason": "", "unexpected": True},
        ).status_code
        == 422
    )


def test_import_job_result_success_is_atomic_bound_and_idempotent() -> None:
    actor = _actor(user_id="import-owner")
    client, container = _client(actor)
    assert container.ports is not None
    container.ports.files["import-source"] = _file("import-source")
    job = _data(
        client.post("/api/v1/qualifications/imports", json={"fileId": "import-source"}),
        202,
    )

    rows = [_import_row("IMPORT-001"), _import_row("IMPORT-002", tags=["导入", "重点"])]
    imported = asyncio.run(
        container.qualifications.apply_import_result(
            tenant_id="tenant-a",
            job_id=job["id"],
            category="qualification.import",
            source_file_id="import-source",
            rows=rows,
        )
    )

    assert [item["certNumber"] for item in imported] == ["IMPORT-001", "IMPORT-002"]
    assert {item["file"]["id"] for item in imported} == {"import-source"}
    assert len(container.qualification_store.qualifications) == 2
    assert len(container.qualification_store.versions) == 2
    binding = container.qualification_store.get_import_binding(job["id"], tenant_id="tenant-a")
    assert (binding.category, binding.source_file_id, binding.actor_id) == (
        "qualification.import",
        "import-source",
        "import-owner",
    )

    repeated = asyncio.run(
        container.qualifications.apply_import_result(
            tenant_id="tenant-a",
            job_id=job["id"],
            category="qualification.import",
            source_file_id="import-source",
            rows=[_import_row("MUST-NOT-BE-WRITTEN")],
        )
    )
    assert repeated == imported
    assert len(container.qualification_store.qualifications) == 2
    assert [event.action for event in container.ports.audits].count("qualification.import_applied") == 1
    assert (
        _data(
            client.post("/api/v1/qualifications/imports", json={"fileId": "import-source"}),
            202,
        )["status"]
        == "succeeded"
    )

    with pytest.raises(DomainError, match="相反的终态结果"):
        asyncio.run(
            container.qualifications.apply_import_failure(
                tenant_id="tenant-a",
                job_id=job["id"],
                category="qualification.import",
                source_file_id="import-source",
                message="迟到的失败结果",
            )
        )


def test_import_idempotency_replay_rechecks_actor_file_access() -> None:
    owner = _actor(user_id="import-owner")
    owner_client, container = _client(owner)
    assert container.ports is not None
    container.ports.files["private-import"] = _file("private-import")
    original_files = container.qualifications.files

    async def assert_owner_access(**kwargs: object) -> FileRefSnapshot:
        if kwargs["actor_id"] != owner.user_id:
            raise KeyError(kwargs["file_id"])
        return await original_files.assert_accessible(**kwargs)  # type: ignore[arg-type]

    access = AsyncMock(side_effect=assert_owner_access)
    container.qualifications.files = SimpleNamespace(assert_accessible=access)  # type: ignore[assignment]
    first = owner_client.post("/api/v1/qualifications/imports", json={"fileId": "private-import"})
    assert first.status_code == 202

    other_client, _ = _client(_actor(user_id="other-lead", role="project_lead"), container)
    replay = other_client.post("/api/v1/qualifications/imports", json={"fileId": "private-import"})

    assert replay.status_code == 404
    assert access.await_count == 2
    assert [call.kwargs["actor_id"] for call in access.await_args_list] == ["import-owner", "other-lead"]
    assert len(container.ports.jobs) == 1


def test_import_job_result_validates_entire_batch_before_any_write() -> None:
    client, container = _client(_actor())
    assert container.ports is not None
    container.ports.files["existing-file"] = _file("existing-file")
    container.ports.files["batch-source"] = _file("batch-source")
    _data(client.post("/api/v1/qualifications", json=_payload(file_id="existing-file", cert_number="EXISTING")), 201)
    baseline_qualifications = len(container.qualification_store.qualifications)
    baseline_versions = len(container.qualification_store.versions)
    job = _data(client.post("/api/v1/qualifications/imports", json={"fileId": "batch-source"}), 202)

    with pytest.raises(DomainError):
        asyncio.run(
            container.qualifications.apply_import_result(
                tenant_id="tenant-a",
                job_id=job["id"],
                category="qualification.import",
                source_file_id="batch-source",
                rows=[_import_row("DUPLICATE"), _import_row("duplicate")],
            )
        )
    assert len(container.qualification_store.qualifications) == baseline_qualifications
    assert len(container.qualification_store.versions) == baseline_versions

    with pytest.raises(DomainError):
        asyncio.run(
            container.qualifications.apply_import_result(
                tenant_id="tenant-a",
                job_id=job["id"],
                category="qualification.import",
                source_file_id="batch-source",
                rows=[_import_row("NEW-FIRST"), _import_row("EXISTING")],
            )
        )
    assert len(container.qualification_store.qualifications) == baseline_qualifications
    assert len(container.qualification_store.versions) == baseline_versions

    container.ports.files["batch-source"] = _file("batch-source", scan_status="infected")
    with pytest.raises(DomainError) as rejected:
        asyncio.run(
            container.qualifications.apply_import_result(
                tenant_id="tenant-a",
                job_id=job["id"],
                category="qualification.import",
                source_file_id="batch-source",
                rows=[_import_row("CLEAN-ONLY")],
            )
        )
    assert rejected.value.code == "FILE_REJECTED"
    assert len(container.qualification_store.qualifications) == baseline_qualifications
    assert len(container.qualification_store.versions) == baseline_versions


def test_import_job_failure_is_bound_idempotent_and_has_no_business_writes() -> None:
    actor = _actor(user_id="failure-owner")
    client, container = _client(actor)
    assert container.ports is not None
    container.ports.files["failure-source"] = _file("failure-source")
    job = _data(client.post("/api/v1/qualifications/imports", json={"fileId": "failure-source"}), 202)

    with pytest.raises(DomainError):
        asyncio.run(
            container.qualifications.apply_import_failure(
                tenant_id="tenant-b",
                job_id=job["id"],
                category="qualification.import",
                source_file_id="failure-source",
                message="错误租户",
            )
        )
    with pytest.raises(DomainError):
        asyncio.run(
            container.qualifications.apply_import_failure(
                tenant_id="tenant-a",
                job_id=job["id"],
                category="wrong.category",
                source_file_id="failure-source",
                message="错误类别",
            )
        )
    with pytest.raises(DomainError):
        asyncio.run(
            container.qualifications.apply_import_failure(
                tenant_id="tenant-a",
                job_id=job["id"],
                category="qualification.import",
                source_file_id="other-source",
                message="错误源文件",
            )
        )

    failed = asyncio.run(
        container.qualifications.apply_import_failure(
            tenant_id="tenant-a",
            job_id=job["id"],
            category="qualification.import",
            source_file_id="failure-source",
            message="解析失败",
        )
    )
    repeated = asyncio.run(
        container.qualifications.apply_import_failure(
            tenant_id="tenant-a",
            job_id=job["id"],
            category="qualification.import",
            source_file_id="failure-source",
            message="不得覆盖首个结果",
        )
    )
    assert repeated == failed == {"jobId": job["id"], "status": "failed", "message": "解析失败"}
    assert container.qualification_store.qualifications == {}
    assert container.qualification_store.versions == {}
    assert [event.action for event in container.ports.audits].count("qualification.import_failed") == 1
    assert len(container.ports.notifications) == 1
    assert container.ports.notifications[0].user_id == "failure-owner"
    assert (
        _data(
            client.post("/api/v1/qualifications/imports", json={"fileId": "failure-source"}),
            202,
        )["status"]
        == "failed"
    )

    with pytest.raises(DomainError, match="相反的终态结果"):
        asyncio.run(
            container.qualifications.apply_import_result(
                tenant_id="tenant-a",
                job_id=job["id"],
                category="qualification.import",
                source_file_id="failure-source",
                rows=[_import_row("LATE-SUCCESS")],
            )
        )


def test_import_success_does_not_commit_when_audit_write_fails() -> None:
    client, container = _client(_actor())
    assert container.ports is not None
    container.ports.files["audit-source"] = _file("audit-source")
    job = _data(client.post("/api/v1/qualifications/imports", json={"fileId": "audit-source"}), 202)
    container.qualifications.audit = SimpleNamespace(append=AsyncMock(side_effect=RuntimeError("audit unavailable")))  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="audit unavailable"):
        asyncio.run(
            container.qualifications.apply_import_result(
                tenant_id="tenant-a",
                job_id=job["id"],
                category="qualification.import",
                source_file_id="audit-source",
                rows=[_import_row("AUDIT-FAIL")],
            )
        )
    assert container.qualification_store.qualifications == {}
    assert container.qualification_store.versions == {}
    assert container.qualification_store.import_results == {}


def test_import_job_model_persists_binding_and_terminal_fields() -> None:
    from app.domains.qualifications.models import QualificationImportJobModel

    assert {
        "tenant_id",
        "file_id",
        "job_id",
        "category",
        "status",
        "created_by",
        "actor_name",
        "actor_role",
        "result_payload",
        "failure_message",
        "completed_at",
    } <= set(QualificationImportJobModel.__table__.columns.keys())
