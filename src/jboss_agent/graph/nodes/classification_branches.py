"""Tiny STEP 2 nodes that make Conditional Edge destinations observable."""

from __future__ import annotations

from collections.abc import Callable

from jboss_agent.graph.state import MonitoringState


def _branch_node(name: str) -> Callable[[MonitoringState], dict[str, object]]:
    def node(state: MonitoringState) -> dict[str, object]:
        trace = [*state.get("node_trace", []), name]
        return {"route_taken": name, "node_trace": trace}

    return node


normal_branch = _branch_node("normal_branch")
thread_pool_branch = _branch_node("thread_pool_branch")
datasource_pool_branch = _branch_node("datasource_pool_branch")
deployment_branch = _branch_node("deployment_branch")
unknown_branch = _branch_node("unknown_branch")
