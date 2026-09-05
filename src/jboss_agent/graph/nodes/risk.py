"""STEP 7 deterministic risk/validation node."""

from __future__ import annotations

from jboss_agent.domain.risk_policy import evaluate_action
from jboss_agent.graph.state import IncidentState


def validate_proposed_action(state: IncidentState) -> dict[str, object]:
    result = evaluate_action(state.get("proposed_action"))
    trace = [*state.get("node_trace", []), "validate_proposed_action"]
    return {
        "proposed_action": result.normalized_action,
        "risk_level": result.risk,
        "policy_reason": result.reason,
        "approval_status": "PENDING" if result.allowed and result.risk != "LOW" else None,
        "node_trace": trace,
    }


def route_after_policy(state: IncidentState) -> str:
    if state.get("risk_level") == "BLOCKED":
        return "blocked"
    if (state.get("proposed_action") or {}).get("type") == "NONE":
        return "no_action"
    return "approval"
