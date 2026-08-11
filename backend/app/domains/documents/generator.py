"""Build downloadable DOCX files from validated, paragraph-level AI output."""

from __future__ import annotations

import io
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape, quoteattr

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"


@dataclass(frozen=True, slots=True)
class EmbeddedImage:
    file_id: str
    content: bytes
    mime_type: str


@dataclass(frozen=True, slots=True)
class GeneratedDocx:
    content: bytes
    embedded_image_count: int
    missing_image_ids: tuple[str, ...]


class _DocumentRenderer:
    def __init__(self, images: Mapping[str, EmbeddedImage]) -> None:
        self.images = images
        self.relationships: list[str] = []
        self.media: dict[str, bytes] = {}
        self.image_relationships: dict[str, tuple[str, str]] = {}
        self.missing_image_ids: list[str] = []
        self.next_relationship_id = 2  # rId1 is styles.xml
        self.next_drawing_id = 1

    def render_image(self, anchor: Mapping[str, Any]) -> str:
        file_id = str(anchor.get("fileId") or "").strip()
        caption = str(anchor.get("caption") or file_id or "未命名图片").strip()
        alt_text = str(anchor.get("altText") or caption).strip()
        image = self.images.get(file_id)
        if image is None:
            if file_id and file_id not in self.missing_image_ids:
                self.missing_image_ids.append(file_id)
            return _paragraph(f"[图片暂不可用：{caption}（文件 {file_id or '未知'}）]", style="Caption")

        relation = self.image_relationships.get(file_id)
        if relation is None:
            extension, content_type = _image_format(image)
            relation_id = f"rId{self.next_relationship_id}"
            self.next_relationship_id += 1
            media_name = f"image{len(self.media) + 1}.{extension}"
            self.relationships.append(
                f'<Relationship Id="{relation_id}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                f'Target="media/{media_name}"/>'
            )
            self.media[media_name] = image.content
            self.image_relationships[file_id] = (relation_id, content_type)
        else:
            relation_id, content_type = relation
        _ = content_type

        drawing_id = self.next_drawing_id
        self.next_drawing_id += 1
        width = 5_303_520
        height = 2_982_240
        drawing = (
            '<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
            '<wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{width}" cy="{height}"/>'
            f'<wp:docPr id="{drawing_id}" name={quoteattr(caption)} descr={quoteattr(alt_text)}/>'
            '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            "<pic:pic><pic:nvPicPr>"
            f'<pic:cNvPr id="0" name={quoteattr(caption)}/><pic:cNvPicPr/>'
            "</pic:nvPicPr><pic:blipFill>"
            f'<a:blip r:embed="{relation_id}"/><a:stretch><a:fillRect/></a:stretch>'
            '</pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/>'
            f'<a:ext cx="{width}" cy="{height}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
            "</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>"
        )
        return drawing + _paragraph(caption, style="Caption", centered=True)


def build_bid_docx(
    *,
    title: str,
    template_name: str,
    sections: Sequence[Mapping[str, Any]],
    images: Mapping[str, EmbeddedImage] | None = None,
    include_watermark: bool = False,
) -> GeneratedDocx:
    """Create a valid Word package while preserving section/paragraph/image order."""

    renderer = _DocumentRenderer(images or {})
    body_parts = [
        _paragraph(title.strip() or "投标文件", style="Title", centered=True),
        _paragraph(f"模板：{template_name.strip() or '标准模板'}", style="Subtitle", centered=True),
    ]
    for raw_section in sections:
        section = dict(raw_section)
        heading = str(section.get("heading") or section.get("section") or "未命名章节").strip()
        heading_level = _bounded_int(section.get("headingLevel"), minimum=1, maximum=3, default=1)
        paragraphs = section.get("paragraphs")
        if not isinstance(paragraphs, list):
            paragraphs = []
        anchors = section.get("images")
        if not isinstance(anchors, list):
            anchors = []

        for anchor in _anchors(anchors, placement="before_section"):
            body_parts.append(renderer.render_image(anchor))
        body_parts.append(_paragraph(heading, style=f"Heading{heading_level}"))
        if not paragraphs:
            body_parts.append(_paragraph("本章节暂无生成内容，请人工补充并复核。"))
        for fallback_index, raw_paragraph in enumerate(paragraphs, start=1):
            if isinstance(raw_paragraph, Mapping):
                paragraph_index = _bounded_int(
                    raw_paragraph.get("index"), minimum=1, maximum=10_000, default=fallback_index
                )
                text = str(raw_paragraph.get("text") or raw_paragraph.get("paragraph") or "").strip()
                evidence = raw_paragraph.get("evidence")
            else:
                paragraph_index = fallback_index
                text = str(raw_paragraph).strip()
                evidence = None
            body_parts.append(_paragraph(text or "[本段生成内容为空，请人工补充]"))
            evidence_text = _evidence_text(evidence)
            if evidence_text:
                body_parts.append(_paragraph(f"依据：{evidence_text}", style="Evidence"))
            for anchor in _anchors(anchors, placement="after_paragraph", paragraph_index=paragraph_index):
                body_parts.append(renderer.render_image(anchor))
        for anchor in _anchors(anchors, placement="after_section"):
            body_parts.append(renderer.render_image(anchor))

    sect_properties = (
        "<w:sectPr>"
        + ('<w:headerReference w:type="default" r:id="rIdHeader"/>' if include_watermark else "")
        + '<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" '
        'w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
    )
    document_xml = _document_xml("".join(body_parts) + sect_properties)
    document_relationships = [
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    ]
    if include_watermark:
        document_relationships.append(
            '<Relationship Id="rIdHeader" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" '
            'Target="header1.xml"/>'
        )
    document_relationships.extend(renderer.relationships)

    package: dict[str, bytes] = {
        "[Content_Types].xml": _content_types_xml(renderer.media, include_watermark).encode(),
        "_rels/.rels": _root_relationships_xml().encode(),
        "word/document.xml": document_xml.encode(),
        "word/styles.xml": _styles_xml().encode(),
        "word/_rels/document.xml.rels": _relationships_xml(document_relationships).encode(),
    }
    if include_watermark:
        package["word/header1.xml"] = _header_xml().encode()
    for name, content in renderer.media.items():
        package[f"word/media/{name}"] = content

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(package):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, package[name])
    return GeneratedDocx(
        content=output.getvalue(),
        embedded_image_count=len(renderer.media),
        missing_image_ids=tuple(renderer.missing_image_ids),
    )


def _image_format(image: EmbeddedImage) -> tuple[str, str]:
    mime_type = image.mime_type.lower().strip()
    if mime_type == "image/png" and image.content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if mime_type in {"image/jpeg", "image/jpg"} and image.content.startswith(b"\xff\xd8"):
        return "jpg", "image/jpeg"
    raise ValueError(f"unsupported or invalid image content for {image.file_id}")


def _anchors(
    anchors: Sequence[Any],
    *,
    placement: str,
    paragraph_index: int | None = None,
) -> list[Mapping[str, Any]]:
    matched: list[Mapping[str, Any]] = []
    for anchor in anchors:
        if not isinstance(anchor, Mapping) or anchor.get("placement") != placement:
            continue
        if placement == "after_paragraph" and anchor.get("afterParagraphIndex") != paragraph_index:
            continue
        matched.append(anchor)
    return matched


def _evidence_text(raw: Any) -> str:
    if not isinstance(raw, list):
        return ""
    parts: list[str] = []
    for item in raw:
        if isinstance(item, Mapping):
            source = str(item.get("sourceId") or item.get("sourceType") or "").strip()
            summary = str(item.get("summary") or item.get("quote") or "").strip()
            value = " - ".join(part for part in (source, summary) if part)
        else:
            value = str(item).strip()
        if value:
            parts.append(value)
    return "；".join(parts)


def _paragraph(
    text: str,
    *,
    style: str | None = None,
    centered: bool = False,
) -> str:
    properties: list[str] = []
    if style:
        properties.append(f'<w:pStyle w:val="{escape(style)}"/>')
    if centered:
        properties.append('<w:jc w:val="center"/>')
    p_properties = f"<w:pPr>{''.join(properties)}</w:pPr>" if properties else ""
    return f'<w:p>{p_properties}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def _document_xml(body: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W_NS}" xmlns:r="{_R_NS}" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f"<w:body>{body}</w:body></w:document>"
    )


def _root_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{_REL_NS}">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>'
    )


def _relationships_xml(relationships: Sequence[str]) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{_REL_NS}">{"".join(relationships)}</Relationships>'
    )


def _content_types_xml(media: Mapping[str, bytes], include_watermark: bool) -> str:
    extensions = {name.rsplit(".", 1)[-1] for name in media}
    defaults = [
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
    ]
    if "png" in extensions:
        defaults.append('<Default Extension="png" ContentType="image/png"/>')
    if "jpg" in extensions:
        defaults.append('<Default Extension="jpg" ContentType="image/jpeg"/>')
    overrides = [
        f'<Override PartName="/word/document.xml" ContentType="{_DOCX_MIME}.main+xml"/>',
        '<Override PartName="/word/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>',
    ]
    if include_watermark:
        overrides.append(
            '<Override PartName="/word/header1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Types xmlns="{_CONTENT_TYPES_NS}">{"".join(defaults)}{"".join(overrides)}</Types>'
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:styles xmlns:w="{_W_NS}">'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/><w:rPr><w:rFonts w:eastAsia="宋体"/><w:sz w:val="24"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/>'
        '<w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/>'
        '<w:basedOn w:val="Normal"/><w:rPr><w:color w:val="666666"/><w:sz w:val="20"/></w:rPr></w:style>'
        + "".join(
            f'<w:style w:type="paragraph" w:styleId="Heading{level}"><w:name w:val="heading {level}"/>'
            f'<w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="{34 - level * 4}"/></w:rPr></w:style>'
            for level in range(1, 4)
        )
        + '<w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="Caption"/>'
        '<w:basedOn w:val="Normal"/><w:rPr><w:color w:val="666666"/><w:sz w:val="20"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Evidence"><w:name w:val="Evidence"/>'
        '<w:basedOn w:val="Normal"/><w:rPr><w:color w:val="777777"/><w:sz w:val="18"/></w:rPr></w:style>'
        "</w:styles>"
    )


def _header_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:hdr xmlns:w="{_W_NS}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
        '<w:r><w:rPr><w:color w:val="D0D0D0"/><w:sz w:val="32"/></w:rPr>'
        "<w:t>投标文件 · 演示水印</w:t></w:r></w:p></w:hdr>"
    )


def _bounded_int(value: Any, *, minimum: int, maximum: int, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    number = int(value)
    return min(maximum, max(minimum, number))


__all__ = ["EmbeddedImage", "GeneratedDocx", "build_bid_docx"]
