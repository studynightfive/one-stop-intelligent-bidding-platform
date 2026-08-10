"""文档 diff：基于 section 切片的纯文本对比。"""

from __future__ import annotations

from collections.abc import Iterable

from app.domains.documents.entities import DocumentChangeEntity, DocumentVersionEntity
from app.domains.documents.hashing import normalize_section


def parse_sections(text: str) -> dict[str, str]:
    """把文档按 `## section` 切分为 {section_name: content}。

    兼容 Word 文本提取后常见的大小写/空白差异。无法识别 section 的内容归入
    "__body__" 段落。"""
    sections: dict[str, list[str]] = {"__body__": []}
    current: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            current = normalize_section(stripped[3:])
            sections.setdefault(current, [])
        else:
            target = current if current is not None else "__body__"
            sections.setdefault(target, []).append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def diff_sections(before_text: str, after_text: str) -> list[DocumentChangeEntity]:
    """返回两段文本之间的 diff。"""
    before_map = parse_sections(before_text)
    after_map = parse_sections(after_text)
    changes: list[DocumentChangeEntity] = []
    for section in sorted(set(before_map) | set(after_map)):
        before_val = before_map.get(section)
        after_val = after_map.get(section)
        if before_val == after_val:
            continue
        if before_val is None and after_val is not None:
            changes.append(DocumentChangeEntity(section=section, change_type="added", after=after_val))
        elif after_val is None and before_val is not None:
            changes.append(DocumentChangeEntity(section=section, change_type="removed", before=before_val))
        else:
            changes.append(
                DocumentChangeEntity(
                    section=section,
                    change_type="changed",
                    before=before_val,
                    after=after_val,
                )
            )
    return changes


def summarise_changes(changes: Iterable[DocumentChangeEntity]) -> dict[str, int]:
    counts = {"added": 0, "removed": 0, "changed": 0}
    for change in changes:
        if change.change_type in counts:
            counts[change.change_type] += 1
    return counts


def preview_diff_text(version: DocumentVersionEntity, *, max_length: int = 200) -> str:
    """生成版本变更的简短预览（仅用于回滚时 change_summary 兜底）。"""
    summary = (version.change_summary or "").strip()
    if summary:
        return summary[:max_length]
    return f"v{version.version_number} by {version.created_by_name}"
