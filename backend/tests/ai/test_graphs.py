"""LangGraph 状态机测试。"""

from __future__ import annotations

import pytest

from app.ai.graphs.base import EchoNode, GraphRunner, GraphState


@pytest.mark.asyncio
async def test_echo_node_returns_state() -> None:
    state = GraphState(job_id="job-1", scene="tender_parse", payload={"x": 1})
    node = EchoNode()
    result = await node(state)
    assert result.output == {"echo": True, "scene": "tender_parse", "jobId": "job-1"}
    assert "echo" in result.attempts


@pytest.mark.asyncio
async def test_graph_runner_runs_all_nodes() -> None:
    state = GraphState(job_id="job-1", scene="tender_parse")
    runner = GraphRunner(nodes=[EchoNode(name="a"), EchoNode(name="b")])
    final = await runner.run(state)
    assert final.attempts == ["a", "b"]
    assert final.output is not None


@pytest.mark.asyncio
async def test_graph_runner_records_error() -> None:
    class FailingNode:
        name = "fail"

        async def __call__(self, state: GraphState) -> GraphState:
            raise RuntimeError("boom")

    state = GraphState(job_id="job-1", scene="tender_parse")
    runner = GraphRunner(nodes=[EchoNode(), FailingNode()])
    final = await runner.run(state)
    assert final.error is not None
    assert "fail" in final.error


def test_build_default_runner_returns_runner() -> None:
    from app.ai.graphs.base import build_default_runner

    runner = build_default_runner()
    assert isinstance(runner, GraphRunner)
