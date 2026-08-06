"""L0 独占的领域 Router 聚合器。"""

from fastapi import APIRouter

api_router = APIRouter()

# 领域 Router 在对应成员 PR 合并后由 L0 在此显式 include_router。
# 该文件不得放置任何业务处理逻辑。
