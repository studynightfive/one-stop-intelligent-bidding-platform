"""文档哈希与版本元数据辅助。"""

from __future__ import annotations

import hashlib


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def normalize_section(section: str) -> str:
    """小写、去空白，便于 diff 时 section 名称对齐。"""
    return section.strip().lower()


def section_key(*parts: str) -> str:
    return "::".join(normalize_section(p) for p in parts if p)
