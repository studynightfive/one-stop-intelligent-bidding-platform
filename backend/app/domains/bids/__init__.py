"""M5 投标域（bids）：任务、材料、审核、文档编排。

公开入口：
- ``router`` —— FastAPI 路由
- ``build_m5_bids_container_with_m4`` —— L0 集成容器构造
- ``M5BidTaskSnapshotAdapter`` —— 满足 M6 协议的 ``BidTaskSnapshotPort`` 实现
"""

from app.domains.bids.container import (
    M5BidsContainer,
    build_m5_bids_container,
    build_m5_bids_container_with_m4,
)
from app.domains.bids.m4_adapters import M5BidTaskSnapshotAdapter
from app.domains.bids.router import router

__all__ = [
    "M5BidsContainer",
    "M5BidTaskSnapshotAdapter",
    "build_m5_bids_container",
    "build_m5_bids_container_with_m4",
    "router",
]
