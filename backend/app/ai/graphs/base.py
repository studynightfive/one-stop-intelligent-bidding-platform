"""LangGraph 状态机基础。

本模块为后续 Phase 2/3 的业务状态机预留接口：
- :class:`GraphNode`：业务无关的最小节点协议；
- :class:`GraphRunner`：执行入口，串起 ``router → provider → 后置处理``。

Phase 1 仅保留接口与一个无副作用的演示节点，
确保 M5/M6 业务依赖稳定后再扩展。
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass
class GraphState:
    """LangGraph 节点间共享状态。"""

    job_id: str
    scene: str
    payload: dict[str, Any] = field(default_factory=dict)
    attempts: list[str] = field(default_factory=list)
    prompt_versions: list[str] = field(default_factory=list)
    output: dict[str, Any] | None = None
    error: str | None = None


class GraphNode(Protocol):
    """图节点协议。"""

    name: str

    async def __call__(self, state: GraphState) -> GraphState: ...


@dataclass
class EchoNode:
    """演示节点：仅记录调用，不修改 payload，便于 Phase 1 联调。"""

    name: str = "echo"

    async def __call__(self, state: GraphState) -> GraphState:
        state.attempts.append(self.name)
        state.output = {
            "echo": True,
            "scene": state.scene,
            "jobId": state.job_id,
        }
        return state


class GraphRunner:
    """图执行器：按声明顺序串行调用节点。"""

    def __init__(self, nodes: list[GraphNode]) -> None:
        self._nodes = list(nodes)

    async def run(self, state: GraphState) -> GraphState:
        for node in self._nodes:
            try:
                state = await node(state)
            except Exception as exc:  # noqa: BLE001
                logger.warning("graph.node_failed name=%s err=%s", node.name, exc)
                state.error = f"{node.name}: {exc}"
                return state
        return state


def build_default_runner() -> GraphRunner:
    return GraphRunner(nodes=[EchoNode()])


__all__ = [
    "EchoNode",
    "GraphNode",
    "GraphRunner",
    "GraphState",
    "build_default_runner",
]


# 仅用于类型注解
_ = (Mapping,)
