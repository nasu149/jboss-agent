"""Small terminal/status nodes used by STEP 7-9."""

from __future__ import annotations

from jboss_agent.graph.state import IncidentState


def approved_ready(state: IncidentState) -> dict[str, object]:
    return {"node_trace": [*state.get("node_trace", []), "approved_ready"]}


def rejected(state: IncidentState) -> dict[str, object]:
    return {
        "failure_reason": "Human rejected the proposed write operation.",
        "node_trace": [*state.get("node_trace", []), "rejected"],
    }


def blocked(state: IncidentState) -> dict[str, object]:
    return {
        "approval_status": "BLOCKED",
        "failure_reason": state.get("policy_reason") or "Action blocked by policy.",
        "node_trace": [*state.get("node_trace", []), "blocked"],
    }


def no_action(state: IncidentState) -> dict[str, object]:
    return {
        "recovered": True,
        "node_trace": [*state.get("node_trace", []), "no_action"],
    }


def recovered(state: IncidentState) -> dict[str, object]:
    return {"node_trace": [*state.get("node_trace", []), "recovered"]}


def fail_safe(state: IncidentState) -> dict[str, object]:
    return {
        "recovered": False,
        "failure_reason": "Maximum recovery attempts reached; escalate to a human operator.",
        "node_trace": [*state.get("node_trace", []), "fail_safe"],
    }
