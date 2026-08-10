"""M5 片段库领域公开入口。"""

from app.domains.fragments.ports import (
    SemanticSearchHit,
    SemanticSearchPort,
    SemanticSearchRequest,
    SemanticSearchResult,
)
from app.domains.fragments.router import router
from app.domains.fragments.service import FragmentService
from app.domains.fragments.store import FragmentStore

__all__ = [
    "FragmentService",
    "FragmentStore",
    "SemanticSearchHit",
    "SemanticSearchPort",
    "SemanticSearchRequest",
    "SemanticSearchResult",
    "router",
]
