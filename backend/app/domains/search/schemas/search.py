"""搜索schemas."""

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    """搜索结果项."""

    type: str = Field(..., description="类型: page/bidTask/evaluation/qualification/fragment")
    id: str = Field(..., description="ID")
    title: str = Field(..., description="标题")
    subtitle: str | None = Field(None, description="副标题")
    route: str = Field(..., description="路由")
    score: float = Field(..., description="相关性分数")


class SearchResponse(BaseModel):
    """搜索响应."""

    results: list[SearchResultItem] = Field(..., description="搜索结果列表")
    total: int = Field(..., description="总数")
    query: str = Field(..., description="搜索关键词")
