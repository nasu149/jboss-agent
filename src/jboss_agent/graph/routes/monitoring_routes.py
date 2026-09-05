"""Conditional routing functions for the STEP 2 monitoring graph."""

from __future__ import annotations

from typing import Literal

from jboss_agent.graph.state import MonitoringState


ClassificationRoute = Literal[
    "normal_branch",
    "thread_pool_branch",
    "datasource_pool_branch",
    "deployment_branch",
    "unknown_branch",
]

_CATEGORY_TO_ROUTE: dict[str, ClassificationRoute] = {
    "NORMAL": "normal_branch",
    "THREAD_POOL": "thread_pool_branch",
    "DATASOURCE_POOL": "datasource_pool_branch",
    "DEPLOYMENT": "deployment_branch",
    "UNKNOWN": "unknown_branch",
}


def route_by_category(state: MonitoringState) -> ClassificationRoute:
    """Choose the next node using the validated category already in State.

    The LLM classifies; ordinary Python owns the graph transition mapping.
    """

    category = state.get("category")
    if category is None:
        raise ValueError("category is missing; analyze_logs must run before routing")
    return _CATEGORY_TO_ROUTE[category]
