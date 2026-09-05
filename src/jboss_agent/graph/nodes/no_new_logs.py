"""STEP 3 branch used to make the no-change path observable."""

from __future__ import annotations

from jboss_agent.graph.state import CursorMonitoringState


def no_new_logs(state: CursorMonitoringState) -> dict[str, object]:
    trace = [*state.get("node_trace", []), "no_new_logs"]
    return {"route_taken": "no_new_logs", "node_trace": trace}
