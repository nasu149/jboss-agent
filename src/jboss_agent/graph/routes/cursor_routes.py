"""STEP 3 route that prevents unnecessary LLM calls when no log delta exists."""

from __future__ import annotations

from typing import Literal

from jboss_agent.graph.state import CursorMonitoringState


NewLogRoute = Literal["analyze_logs", "no_new_logs"]


def route_on_new_logs(state: CursorMonitoringState) -> NewLogRoute:
    return "analyze_logs" if state.get("has_new_logs", False) else "no_new_logs"
