"""Real document bytes, hashes, comparisons, tenant isolation and rollback history."""

from __future__ import annotations

import io
import itertools
import zipfile
from hashlib import sha256
from html import escape
from xml.etree import ElementTree

import pytest

from app.contracts.generated.models import DocumentDiff, DocumentVersion
from app.domains.bids.binary import make_docx_bytes
from app.domains.documents.docx import extract_docx_text
from app.domains.documents.errors import DomainError
from app.domains.documents.repository import DocumentStore
from app.domains.documents.service import DocumentService


def _id_factory():
    sequence = itertools.count(1)
    return lambda: f"id-{next(sequence)}"


def _replace_docx_part(content: bytes, part_name: str, replacement: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(content)) as source, zipfile.ZipFile(output, "w") as target:
        for item in source.infolist():
            target.writestr(item, replacement if item.filename == part_name else source.read(item))
    return output.getvalue()


def _make_docx(*paragraphs: str) -> bytes:
    body = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{escape(paragraph)}</w:t></w:r></w:p>' for paragraph in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    ).encode()
    base = make_docx_bytes(sections=[], project_name="placeholder")
    return _replace_docx_part(base, "word/document.xml", document_xml)


def test_generated_docx_has_valid_package_structure_and_escaped_xml() -> None:
    content = make_docx_bytes(
        sections=["technical", "commercial"],
        project_name="A&B <建设项目>",
    )
    assert content.startswith(b"PK")
    with zipfile.ZipFile(io.BytesIO(content)) as package:
        assert set(package.namelist()) == {
            "[Content_Types].xml",
            "_rels/.rels",
            "word/document.xml",
        }
        document_xml = package.read("word/document.xml")
        root = ElementTree.fromstring(document_xml)
    text = "".join(root.itertext())
    assert "A&B <建设项目>" in text
    assert "## technical" in text


def test_extract_docx_text_returns_canonical_paragraph_text() -> None:
    content = _make_docx("建设项目", "## 技术方案", "方案 A & B", "## 商务报价", "100")

    assert extract_docx_text(content) == "建设项目\n## 技术方案\n方案 A & B\n## 商务报价\n100"


@pytest.mark.parametrize(
    ("part_name", "replacement"),
    [
        (
            "[Content_Types].xml",
            b'<Types><Override PartName="/word/document.xml" ContentType="text/xml"/></Types>',
        ),
        (
            "_rels/.rels",
            (
                b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                b'<Relationship Id="rId1" '
                b'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                b'Target="word/other.xml"/></Relationships>'
            ),
        ),
        ("word/document.xml", b"<document><body>fake Word XML</body></document>"),
        ("word/document.xml", b"<w:document"),
    ],
    ids=["wrong-content-type", "wrong-relationship", "fake-word-xml", "malformed-word-xml"],
)
def test_extract_docx_text_rejects_invalid_opc_parts(part_name: str, replacement: bytes) -> None:
    content = _replace_docx_part(
        make_docx_bytes(sections=["technical"], project_name="validation"),
        part_name,
        replacement,
    )

    with pytest.raises(DomainError) as invalid:
        extract_docx_text(content)
    assert invalid.value.code == "VALIDATION_ERROR"


def test_append_validates_complete_docx_before_writing() -> None:
    store = DocumentStore()
    service = DocumentService(store)
    content = _replace_docx_part(
        make_docx_bytes(sections=["technical"], project_name="validation"),
        "_rels/.rels",
        b"<Relationships/>",
    )

    with pytest.raises(DomainError) as invalid:
        service.append_version(
            tenant_id="tenant-a",
            task_id="task-1",
            doc_type="technical",
            new_id_fn=_id_factory(),
            file_id="file-invalid",
            file_name="invalid.docx",
            size_bytes=len(content),
            content=content,
            sha256=sha256(content).hexdigest(),
            text_content="untrusted",
        )
    assert invalid.value.code == "VALIDATION_ERROR"
    assert store.documents == {}
    assert store.versions == {}


def test_hash_compare_and_rollback_as_new_version_preserve_all_history() -> None:
    store = DocumentStore()
    service = DocumentService(store)
    new_id = _id_factory()
    first_content = _make_docx("项目", "## 技术方案", "方案 A", "## 商务报价", "100")
    second_content = _make_docx(
        "项目",
        "## 技术方案",
        "方案 B",
        "## 商务报价",
        "100",
        "## 资质",
        "齐全",
    )

    first = service.append_version(
        tenant_id="tenant-a",
        task_id="task-1",
        doc_type="technical",
        new_id_fn=new_id,
        file_id="file-v1",
        file_name="technical-v1.docx",
        size_bytes=len(first_content),
        content=first_content,
        sha256=sha256(first_content).hexdigest(),
        text_content="## 伪造文本\n不应参与比较",
        change_summary="初始版本",
        created_by_id="user-1",
        created_by_name="负责人",
    )
    second = service.append_version(
        tenant_id="tenant-a",
        task_id="task-1",
        doc_type="technical",
        new_id_fn=new_id,
        file_id="file-v2",
        file_name="technical-v2.docx",
        size_bytes=len(second_content),
        content=second_content,
        sha256=sha256(second_content).hexdigest(),
        text_content="## 伪造文本\n不应参与比较",
        change_summary="补充资质并更新方案",
        created_by_id="user-1",
        created_by_name="负责人",
    )

    assert first.version_number == 1
    assert second.version_number == 2
    assert first.sha256 == sha256(first_content).hexdigest()
    assert second.sha256 == sha256(second_content).hexdigest()
    assert first.text_content == extract_docx_text(first_content)
    assert second.text_content == extract_docx_text(second_content)
    assert "伪造文本" not in first.text_content
    comparison = service.compare_versions(
        tenant_id="tenant-a",
        task_id="task-1",
        from_version_id=first.id,
        to_version_id=second.id,
    )
    DocumentDiff.model_validate(comparison)
    changes = {(item["section"], item["type"]) for item in comparison["changes"]}
    assert ("技术方案", "changed") in changes
    assert ("资质", "added") in changes

    rolled_back = service.rollback_to(
        tenant_id="tenant-a",
        task_id="task-1",
        document_id=first.document_id,
        target_version_id=first.id,
        new_id_fn=new_id,
        reason="恢复首版",
        actor_id="user-2",
        actor_name="管理员",
    )
    assert rolled_back.version_number == 3
    assert rolled_back.id not in {first.id, second.id}
    assert rolled_back.source_version_id == first.id
    assert rolled_back.roll_back is True
    assert rolled_back.content == first_content
    assert rolled_back.sha256 == first.sha256
    assert rolled_back.text_content == first.text_content
    DocumentVersion.model_validate(service.build_download_meta(tenant_id="tenant-a", version_id=rolled_back.id))
    assert len(store.get_versions_for_document(document_id=first.document_id)) == 3
    assert store.get_version(second.id, tenant_id="tenant-a").content == second_content


def test_document_versions_are_tenant_isolated_and_hash_mismatch_is_rejected() -> None:
    store = DocumentStore()
    service = DocumentService(store)
    new_id = _id_factory()
    content = make_docx_bytes(sections=["technical"], project_name="租户隔离")
    version = service.append_version(
        tenant_id="tenant-a",
        task_id="task-1",
        doc_type="technical",
        new_id_fn=new_id,
        file_id="file-v1",
        file_name="technical.docx",
        size_bytes=len(content),
        content=content,
        sha256=sha256(content).hexdigest(),
    )

    with pytest.raises(DomainError) as cross_tenant:
        service.get_version(tenant_id="tenant-b", version_id=version.id)
    assert cross_tenant.value.code == "NOT_FOUND"

    with pytest.raises(DomainError) as mismatch:
        service.append_version(
            tenant_id="tenant-a",
            task_id="task-1",
            doc_type="technical",
            new_id_fn=new_id,
            file_id="file-invalid",
            file_name="invalid.docx",
            size_bytes=len(content),
            content=content,
            sha256="0" * 64,
        )
    assert mismatch.value.code == "CONFLICT"
