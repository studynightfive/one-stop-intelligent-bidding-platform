"""片段库语义检索边界。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SemanticSearchRequest:
    tenant_id: str
    query: str
    category: str | None
    offset: int
    limit: int


@dataclass(frozen=True, slots=True)
class SemanticSearchHit:
    fragment_id: str
    match_score: float
    match_reason: str


@dataclass(frozen=True, slots=True)
class SemanticSearchResult:
    hits: tuple[SemanticSearchHit, ...]
    total: int


class SemanticSearchPort(Protocol):
    async def search(self, request: SemanticSearchRequest) -> SemanticSearchResult:
        """返回稳定、租户隔离且无洞的 offset 分页。

        ``total`` 是当前租户和分类下的匹配总数；``hits`` 必须恰好包含
        ``min(limit, max(total - offset, 0))`` 个按相关度稳定排序的结果。
        """
        ...
