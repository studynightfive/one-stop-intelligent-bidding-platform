"""DOCX assembly tests for paragraph-level technical documents."""

from __future__ import annotations

import base64
import io
import zipfile

from app.domains.documents.docx import extract_docx_text
from app.domains.documents.generator import EmbeddedImage, build_bid_docx

_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_build_bid_docx_preserves_paragraphs_evidence_and_image_anchor() -> None:
    generated = build_bid_docx(
        title="智慧园区技术标书",
        template_name="技术标标准模板",
        sections=[
            {
                "key": "architecture",
                "heading": "1 总体架构",
                "headingLevel": 1,
                "paragraphs": [
                    {
                        "index": 1,
                        "text": "第一段说明总体设计。",
                        "evidence": [{"sourceId": "REQ-01", "summary": "招标技术要求"}],
                    },
                    {"index": 2, "text": "第二段说明安全设计。", "evidence": []},
                ],
                "images": [
                    {
                        "fileId": "image-1",
                        "sectionKey": "architecture",
                        "caption": "图 1 系统架构",
                        "altText": "系统架构图",
                        "placement": "after_paragraph",
                        "afterParagraphIndex": 1,
                    }
                ],
            }
        ],
        images={"image-1": EmbeddedImage(file_id="image-1", content=_ONE_PIXEL_PNG, mime_type="image/png")},
        include_watermark=True,
    )

    text = extract_docx_text(generated.content)
    assert "智慧园区技术标书" in text
    assert text.index("第一段说明总体设计") < text.index("图 1 系统架构") < text.index("第二段说明安全设计")
    assert "依据：REQ-01 - 招标技术要求" in text
    assert generated.embedded_image_count == 1
    assert generated.missing_image_ids == ()
    with zipfile.ZipFile(io.BytesIO(generated.content)) as archive:
        assert "word/media/image1.png" in archive.namelist()
        assert "word/header1.xml" in archive.namelist()
        document = archive.read("word/document.xml").decode()
        assert 'r:embed="rId2"' in document


def test_build_bid_docx_marks_missing_images_without_corrupting_package() -> None:
    generated = build_bid_docx(
        title="缺图文档",
        template_name="标准模板",
        sections=[
            {
                "heading": "技术方案",
                "headingLevel": 1,
                "paragraphs": [{"index": 1, "text": "正文", "evidence": []}],
                "images": [
                    {
                        "fileId": "missing-image",
                        "caption": "现场拓扑图",
                        "placement": "after_section",
                    }
                ],
            }
        ],
    )

    assert generated.embedded_image_count == 0
    assert generated.missing_image_ids == ("missing-image",)
    assert "图片暂不可用：现场拓扑图" in extract_docx_text(generated.content)
