"""DOCX package validation and trusted text extraction."""

from __future__ import annotations

import io
import zipfile
from xml.etree import ElementTree

from app.domains.documents.errors import validation_error

_CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
_RELATIONSHIPS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_DOCUMENT_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
_OFFICE_DOCUMENT_RELATIONSHIP_TYPES = {
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
    "http://purl.oclc.org/ooxml/officeDocument/relationships/officeDocument",
}
_WORDPROCESSING_NAMESPACES = {
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "http://purl.oclc.org/ooxml/wordprocessingml/main",
}
_REQUIRED_PARTS = ("[Content_Types].xml", "_rels/.rels", "word/document.xml")
_INVALID_DOCX = "文档内容不是有效的 DOCX"


def extract_docx_text(content: bytes) -> str:
    """Validate the DOCX package and return canonical main-document text."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = archive.namelist()
            if any(names.count(part) != 1 for part in _REQUIRED_PARTS):
                raise validation_error(_INVALID_DOCX)
            content_types = _parse_xml(archive.read("[Content_Types].xml"))
            relationships = _parse_xml(archive.read("_rels/.rels"))
            document = _parse_xml(archive.read("word/document.xml"))
    except (KeyError, NotImplementedError, RuntimeError, zipfile.BadZipFile) as exc:
        raise validation_error(_INVALID_DOCX) from exc

    _validate_content_types(content_types)
    _validate_relationships(relationships)
    word_namespace = _word_namespace(document)
    body = document.find(f"{{{word_namespace}}}body")
    if body is None:
        raise validation_error(_INVALID_DOCX)

    paragraph_tag = f"{{{word_namespace}}}p"
    text_tag = f"{{{word_namespace}}}t"
    tab_tag = f"{{{word_namespace}}}tab"
    break_tags = {f"{{{word_namespace}}}br", f"{{{word_namespace}}}cr"}
    paragraphs: list[str] = []
    for paragraph in body.iter(paragraph_tag):
        parts: list[str] = []
        for element in paragraph.iter():
            if element.tag == text_tag:
                parts.append(element.text or "")
            elif element.tag == tab_tag:
                parts.append("\t")
            elif element.tag in break_tags:
                parts.append("\n")
        paragraphs.append("".join(parts))
    return "\n".join(paragraphs).strip()


def _parse_xml(content: bytes) -> ElementTree.Element:
    if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise validation_error(_INVALID_DOCX)
    try:
        return ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise validation_error(_INVALID_DOCX) from exc


def _validate_content_types(root: ElementTree.Element) -> None:
    if root.tag != f"{{{_CONTENT_TYPES_NS}}}Types":
        raise validation_error(_INVALID_DOCX)
    overrides = [
        element
        for element in root
        if element.tag == f"{{{_CONTENT_TYPES_NS}}}Override" and element.get("PartName") == "/word/document.xml"
    ]
    if len(overrides) != 1 or overrides[0].get("ContentType") != _DOCUMENT_CONTENT_TYPE:
        raise validation_error(_INVALID_DOCX)


def _validate_relationships(root: ElementTree.Element) -> None:
    if root.tag != f"{{{_RELATIONSHIPS_NS}}}Relationships":
        raise validation_error(_INVALID_DOCX)
    office_document_relationships = [
        element
        for element in root
        if element.tag == f"{{{_RELATIONSHIPS_NS}}}Relationship"
        and element.get("Type") in _OFFICE_DOCUMENT_RELATIONSHIP_TYPES
    ]
    if len(office_document_relationships) != 1:
        raise validation_error(_INVALID_DOCX)
    relationship = office_document_relationships[0]
    target = (relationship.get("Target") or "").removeprefix("/")
    if relationship.get("TargetMode", "Internal") != "Internal" or target != "word/document.xml":
        raise validation_error(_INVALID_DOCX)


def _word_namespace(root: ElementTree.Element) -> str:
    for namespace in _WORDPROCESSING_NAMESPACES:
        if root.tag == f"{{{namespace}}}document":
            return namespace
    raise validation_error(_INVALID_DOCX)
