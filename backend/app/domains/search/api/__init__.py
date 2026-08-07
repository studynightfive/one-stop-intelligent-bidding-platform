"""搜索API路由.

实现搜索相关接口：
- GET /global-search - 全局搜索
"""

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import AuthenticatedUser, DBSession
from app.domains.search.schemas.search import SearchResponse


router = APIRouter(prefix="/global-search", tags=["全局搜索"])


@router.get(
    "",
    response_model=SearchResponse,
    summary="全局搜索",
    description="跨模块搜索投标任务、评标任务、资质、文档片段等。",
    responses={200: {"description": "成功"}},
)
async def global_search(
    current_user: AuthenticatedUser,
    db: DBSession,
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
) -> SearchResponse:
    """全局搜索."""
    # TODO: 实现跨模块搜索逻辑
    return SearchResponse(
        results=[],
        total=0,
        query=keyword,
    )
