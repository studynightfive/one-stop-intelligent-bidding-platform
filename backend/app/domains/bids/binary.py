"""M5 二进制响应：材料导出 xlsx、文档下载 docx。"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable
from datetime import UTC, datetime
from html import escape
from typing import Any


def export_materials_xlsx(
    materials: Iterable[Any],
    *,
    project_name: str,
    sheet_name: str = "材料清单",
) -> bytes:
    """使用标准库把材料列表序列化为可打开的 XLSX。"""
    material_list = list(materials)
    headers = [
        "序号",
        "名称",
        "分类",
        "是否必需",
        "要求",
        "状态",
        "来源",
        "关联文件",
        "匹配置信度",
    ]
    rows: list[list[Any]] = [
        ["项目", project_name],
        ["导出时间", datetime.now(UTC).isoformat().replace("+00:00", "Z")],
        [],
        headers,
    ]
    for idx, material in enumerate(material_list, start=1):
        rows.append(
            [
                idx,
                material.name,
                material.category,
                "是" if material.required else "否",
                material.requirement,
                material.status,
                material.source,
                material.file_name or "",
                "" if material.match_confidence is None else round(material.match_confidence, 4),
            ]
        )
    return build_xlsx(rows, sheet_name=sheet_name)


def build_xlsx(rows: Iterable[Iterable[Any]], *, sheet_name: str) -> bytes:
    """构建单工作表 XLSX，避免为简单导出新增运行时依赖。"""
    sheet_rows = []
    for row_number, row in enumerate(rows, start=1):
        cells = []
        for column_number, value in enumerate(row, start=1):
            if value is None:
                continue
            reference = f"{_column_name(column_number)}{row_number}"
            if isinstance(value, bool):
                cells.append(f'<c r="{reference}" t="b"><v>{int(value)}</v></c>')
            elif isinstance(value, int | float):
                cells.append(f'<c r="{reference}"><v>{value}</v></c>')
            else:
                text = escape(str(value))
                cells.append(f'<c r="{reference}" t="inlineStr"><is><t>{text}</t></is></c>')
        sheet_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')

    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    safe_sheet_name = escape((sheet_name or "Sheet1")[:31])
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{safe_sheet_name}" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return buf.getvalue()


def _column_name(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def make_docx_bytes(*, sections: list[str], project_name: str) -> bytes:
    """构建最小可打开 DOCX；生产内容仍由 M7 Worker 生成并经 JobResult 落库。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>',
        )
        zf.writestr("word/document.xml", _doc_xml(project_name=project_name, sections=sections))
    return buf.getvalue()


def _doc_xml(*, project_name: str, sections: list[str]) -> str:
    body = "".join(f"<w:p><w:r><w:t>## {escape(section)}</w:t></w:r></w:p>" for section in sections)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        f"<w:p><w:r><w:t>{escape(project_name)}</w:t></w:r></w:p>"
        f"{body}"
        "</w:body></w:document>"
    )
