"""Observable STEP 4 skip branch."""

from __future__ import annotations

from jboss_agent.graph.state import TeamsNotificationState


def skip_notification(state: TeamsNotificationState) -> dict[str, object]:
    trace = [*state.get("node_trace", []), "skip_notification"]
    return {"route_taken": "skip_notification", "node_trace": trace}
