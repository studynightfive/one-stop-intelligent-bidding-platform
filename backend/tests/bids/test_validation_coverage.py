from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

import pytest

from app.domains.bids.access import (
    can_create,
    can_member_edit,
    can_review,
    can_view,
    is_internal,
    is_owner,
    require_create,
    require_internal,
    require_member_or_owner,
    require_owner,
    require_reviewer,
    require_viewer,
)
from app.domains.bids.entities import BidTaskAssignmentEntity, BidTaskEntity
from app.domains.bids.errors import DomainError
from app.domains.bids.ports import AuthPrincipal, Role
from app.domains.bids.validation import (
    optional_str,
    parse_bool,
    parse_dt,
    parse_enum,
    parse_non_negative_int,
    parse_tags,
    reject_unknown,
    require_id,
    require_str,
    validate_assignment,
    validate_batch_bind,
    validate_create_bid_task,
    validate_create_material,
    validate_create_review,
    validate_document_generate,
    validate_requirements_patch,
    validate_review_decision,
    validate_update_bid_task,
    validate_update_material,
)
from app.domains.documents.diff import diff_sections, preview_diff_text, summarise_changes
from app.domains.documents.entities import DocumentChangeEntity, DocumentVersionEntity


def test_m5_bid_and_document_models_register_expected_tables() -> None:
    from app.domains.bids.models import BidJobBindingModel, BidTaskModel
    from app.domains.documents.models import BidDocumentModel, BidDocumentVersionModel
    from app.models_registry import Base

    expected = {
        "bid_tasks",
        "bid_task_assignments",
        "bid_tender_requirements",
        "bid_materials",
        "bid_review_reports",
        "bid_review_findings",
        "bid_idempotency",
        "bid_job_bindings",
        "bid_documents",
        "bid_document_versions",
    }

    assert expected <= set(Base.metadata.tables)
    assert issubclass(BidTaskModel, Base)
    assert issubclass(BidJobBindingModel, Base)
    assert issubclass(BidDocumentModel, Base)
    assert issubclass(BidDocumentVersionModel, Base)
    assert {"tenant_id", "task_id", "action"} <= set(Base.metadata.tables["bid_job_bindings"].columns.keys())


@pytest.mark.parametrize(
    "invoke",
    [
        pytest.param(lambda: reject_unknown({"extra": True}, set()), id="unknown-field"),
        pytest.param(lambda: parse_bool(1, field="flag"), id="bool-type"),
        pytest.param(lambda: parse_non_negative_int(True, field="count"), id="int-bool"),
        pytest.param(lambda: parse_non_negative_int(-1, field="count"), id="int-range"),
        pytest.param(lambda: require_str({}, "name"), id="required-string"),
        pytest.param(lambda: require_str({"name": "xx"}, "name", max_length=1), id="long-string"),
        pytest.param(lambda: require_id({}, "id"), id="required-id"),
        pytest.param(lambda: require_id({"id": "bad id"}, "id"), id="invalid-id"),
        pytest.param(lambda: parse_dt(None), id="required-datetime"),
        pytest.param(lambda: parse_dt("not-a-date"), id="invalid-datetime"),
        pytest.param(lambda: parse_dt("2026-08-10T12:00:00"), id="timezone-required"),
        pytest.param(lambda: parse_enum("bad", ("good",), field="kind"), id="enum"),
        pytest.param(lambda: parse_tags("tag"), id="tags-type"),
        pytest.param(lambda: parse_tags([""]), id="tag-item"),
        pytest.param(lambda: parse_tags(["same", "same"]), id="duplicate-tags"),
        pytest.param(lambda: optional_str({"note": 1}, "note", max_length=10), id="optional-type"),
        pytest.param(lambda: optional_str({"note": "xx"}, "note", max_length=1), id="optional-length"),
        pytest.param(lambda: validate_batch_bind([]), id="batch-body"),
        pytest.param(lambda: validate_batch_bind({}), id="batch-required"),
        pytest.param(
            lambda: validate_batch_bind({"bindings": [1], "replaceExisting": True}),
            id="batch-item",
        ),
        pytest.param(
            lambda: validate_batch_bind(
                {
                    "bindings": [
                        {"materialId": "m1", "fileId": "f1"},
                        {"materialId": "m1", "fileId": "f2"},
                    ],
                    "replaceExisting": True,
                }
            ),
            id="batch-duplicate",
        ),
        pytest.param(lambda: validate_create_review([]), id="review-body"),
        pytest.param(lambda: validate_create_review({}), id="review-required"),
        pytest.param(lambda: validate_create_review({"types": ["price", "price"]}), id="review-duplicate"),
        pytest.param(
            lambda: validate_create_review({"types": ["price"], "fileVersionIds": "f1"}),
            id="review-files-type",
        ),
        pytest.param(
            lambda: validate_create_review({"types": ["price"], "fileVersionIds": ["bad id"]}),
            id="review-file-id",
        ),
        pytest.param(
            lambda: validate_create_review({"types": ["price"], "fileVersionIds": ["f1", "f1"]}),
            id="review-file-duplicate",
        ),
        pytest.param(lambda: validate_review_decision([]), id="decision-body"),
        pytest.param(lambda: validate_requirements_patch([]), id="requirements-body"),
        pytest.param(lambda: validate_requirements_patch({"projectInfo": []}), id="project-info-type"),
        pytest.param(
            lambda: validate_requirements_patch({"projectInfo": {"name": 1}}),
            id="project-info-value",
        ),
        pytest.param(lambda: validate_requirements_patch({"scoringItems": {}}), id="scoring-type"),
        pytest.param(
            lambda: validate_requirements_patch({"scoringItems": [{"name": "n"}]}),
            id="scoring-fields",
        ),
        pytest.param(
            lambda: validate_requirements_patch({"scoringItems": [{"name": "", "score": "1", "basis": "b"}]}),
            id="scoring-value",
        ),
        pytest.param(
            lambda: validate_requirements_patch({"disqualificationItems": {}}),
            id="disqualification-type",
        ),
        pytest.param(
            lambda: validate_requirements_patch({"qualificationRequirements": {}}),
            id="qualification-type",
        ),
        pytest.param(
            lambda: validate_requirements_patch({"qualificationRequirements": [""]}),
            id="qualification-value",
        ),
        pytest.param(
            lambda: validate_requirements_patch({"technicalRequirements": {}}),
            id="technical-type",
        ),
        pytest.param(lambda: validate_document_generate([]), id="document-body"),
        pytest.param(lambda: validate_document_generate({"sections": []}), id="document-sections"),
        pytest.param(
            lambda: validate_document_generate(
                {
                    "mode": "split",
                    "sections": ["technical", "technical"],
                    "templateMode": "standard",
                    "includeWatermark": False,
                }
            ),
            id="document-duplicate-sections",
        ),
    ],
)
def test_validation_rejects_invalid_inputs(invoke: Callable[[], object]) -> None:
    with pytest.raises(DomainError):
        invoke()


def test_validation_accepts_complete_valid_inputs() -> None:
    deadline = datetime(2026, 8, 10, 12, tzinfo=UTC)

    assert parse_bool(True, field="flag") is True
    assert parse_non_negative_int(0, field="count") == 0
    assert require_str({"name": " value "}, "name") == "value"
    assert require_id({"id": "valid-id_1"}, "id") == "valid-id_1"
    assert parse_dt(deadline) == deadline
    assert parse_dt("2026-08-10T12:00:00Z").tzinfo is not None
    assert parse_enum("good", ("good",), field="kind") == "good"
    assert parse_tags([" first ", "second"]) == ["first", "second"]
    assert optional_str({}, "note", max_length=10) == ""
    assert optional_str({"note": " value "}, "note", max_length=10) == "value"

    created = validate_create_bid_task(
        {
            "projectName": "Project",
            "tenderNo": "TN-1",
            "tenderEntity": "Entity",
            "deadline": deadline,
            "assigneeId": "user-1",
            "tenderFileId": "file-1",
            "tags": ["one"],
            "description": "Description",
        }
    )
    assert created["project_name"] == "Project"
    assert created["description"] == "Description"

    updated = validate_update_bid_task(
        {
            "projectName": "Updated",
            "tenderNo": "TN-2",
            "tenderEntity": "Entity 2",
            "deadline": deadline,
            "assigneeId": "user-2",
            "tags": ["two"],
            "description": "",
        }
    )
    assert updated["project_name"] == "Updated"
    assert updated["description"] is None

    assert validate_assignment({"userId": "user-1", "roleInTask": "owner"})["role_in_task"] == "owner"
    assert (
        validate_create_material(
            {
                "name": "Material",
                "category": "qualification",
                "requirement": "Required",
                "required": True,
                "sortOrder": 0,
            }
        )["source"]
        == "manual"
    )
    assert (
        validate_update_material(
            {
                "name": "Material 2",
                "category": "commercial",
                "requirement": "Updated",
                "required": False,
                "sortOrder": 1,
                "sourceId": "source-1",
            }
        )["source_id"]
        == "source-1"
    )
    assert (
        validate_batch_bind(
            {
                "bindings": [{"materialId": "material-1", "fileId": "file-1"}],
                "replaceExisting": True,
            }
        )["replaceExisting"]
        is True
    )
    assert validate_create_review({"types": ["price", "content"], "fileVersionIds": ["version-1", "version-2"]})[
        "fileVersionIds"
    ] == ["version-1", "version-2"]
    assert validate_review_decision({"decision": "accepted", "comment": "ok"}) == {
        "decision": "accepted",
        "comment": "ok",
    }
    requirements = validate_requirements_patch(
        {
            "projectInfo": {"name": "Project"},
            "scoringItems": [{"name": "Score", "score": "10", "basis": "Rule"}],
            "disqualificationItems": [{"name": "Reject", "basis": "Rule"}],
            "qualificationRequirements": ["Qualification"],
            "technicalRequirements": ["Technical"],
        }
    )
    assert requirements["project_info"] == {"name": "Project"}
    assert (
        validate_document_generate(
            {
                "mode": "split",
                "sections": ["qualification", "technical"],
                "templateMode": "standard",
                "documentTemplateId": "template-1",
                "includeWatermark": False,
            }
        )["documentTemplateId"]
        == "template-1"
    )


def test_bid_access_covers_assignment_roles_and_denials() -> None:
    now = datetime(2026, 8, 10, 12, tzinfo=UTC)
    task = BidTaskEntity(
        id="task-1",
        tenant_id="tenant-1",
        project_name="Project",
        tender_no="TN-1",
        tender_entity="Entity",
        deadline=now,
        status="draft",
        current_step=1,
        progress_percent=0,
        assignee_id="lead-1",
        assignee_name="Lead",
        assignments=[
            BidTaskAssignmentEntity(
                id="assignment-1",
                tenant_id="tenant-1",
                task_id="task-1",
                user_id="member-1",
                user_name="Member",
                role_in_task="collaborator",
                assigned_at=now,
            ),
            BidTaskAssignmentEntity(
                id="assignment-2",
                tenant_id="tenant-1",
                task_id="task-1",
                user_id="reviewer-1",
                user_name="Reviewer",
                role_in_task="reviewer",
                assigned_at=now,
            ),
            BidTaskAssignmentEntity(
                id="assignment-3",
                tenant_id="tenant-1",
                task_id="task-1",
                user_id="lead-2",
                user_name="Second lead",
                role_in_task="owner",
                assigned_at=now,
            ),
        ],
    )

    def actor(user_id: str, role: Role) -> AuthPrincipal:
        return AuthPrincipal(user_id=user_id, tenant_id="tenant-1", name=user_id, role=role)

    admin = actor("admin-1", "admin")
    lead = actor("lead-1", "project_lead")
    assigned_lead = actor("lead-2", "project_lead")
    member = actor("member-1", "member")
    reviewer = actor("reviewer-1", "reviewer")
    outsider = actor("member-2", "member")
    external = actor("supplier-1", cast(Role, "supplier"))

    assert is_internal(admin)
    assert not is_internal(external)
    assert can_create(admin) and can_create(lead) and not can_create(member)
    assert is_owner(admin, task) and is_owner(lead, task) and is_owner(assigned_lead, task)
    assert not is_owner(member, task)
    assert can_view(admin, task) and can_view(lead, task) and can_view(member, task)
    assert not can_view(external, task) and not can_view(outsider, task)
    assert can_member_edit(admin, task) and can_member_edit(lead, task) and can_member_edit(member, task)
    assert not can_member_edit(reviewer, task) and not can_member_edit(outsider, task)
    assert can_review(admin, task) and can_review(lead, task) and can_review(reviewer, task)
    assert not can_review(assigned_lead, task) and not can_review(outsider, task)

    require_internal(admin)
    require_create(lead)
    require_owner(assigned_lead, task)
    require_viewer(member, task)
    require_member_or_owner(member, task)
    require_reviewer(reviewer, task)
    for invoke in (
        lambda: require_internal(external),
        lambda: require_create(member),
        lambda: require_owner(member, task),
        lambda: require_viewer(outsider, task),
        lambda: require_member_or_owner(outsider, task),
        lambda: require_reviewer(outsider, task),
    ):
        with pytest.raises(DomainError):
            invoke()


def test_document_diff_covers_added_removed_changed_and_preview_fallback() -> None:
    changes = diff_sections(
        "intro\n## removed\nold\n## changed\nbefore\n## same\nsame",
        "intro\n## added\nnew\n## changed\nafter\n## same\nsame",
    )

    assert {change.section: change.change_type for change in changes} == {
        "added": "added",
        "changed": "changed",
        "removed": "removed",
    }
    assert summarise_changes([*changes, DocumentChangeEntity(section="ignored", change_type="unknown")]) == {
        "added": 1,
        "removed": 1,
        "changed": 1,
    }

    version = DocumentVersionEntity(
        id="version-1",
        document_id="document-1",
        tenant_id="tenant-1",
        version_number=2,
        file_id="file-1",
        file_name="bid.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=10,
        sha256="sha256",
        change_summary="  updated sections  ",
        created_by_id="user-1",
        created_by_name="User",
        created_at=datetime(2026, 8, 10, 12, tzinfo=UTC),
    )
    assert preview_diff_text(version, max_length=7) == "updated"
    version.change_summary = ""
    assert preview_diff_text(version) == "v2 by User"
