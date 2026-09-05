"""STEP 7 Human-in-the-loop node using interrupt()."""

from __future__ import annotations

from collections.abc import Mapping

from langgraph.types import interrupt

from jboss_agent.domain.models import ApprovalResponse
from jboss_agent.domain.risk_policy import evaluate_action
from jboss_agent.graph.state import IncidentState


def approval_node(state: IncidentState) -> dict[str, object]:
    """Pause before any write side effect.

    IMPORTANT: code before ``interrupt`` may run again on resume. Therefore this
    node only builds a pure JSON payload before pausing; it performs no write or
    notification side effect.
    """

    action = dict(state.get("proposed_action") or {})
    payload = {
        "type": "approval_required",
        "incident_id": state["incident_id"],
        "server_id": state["server_id"],
        "action": action.get("type"),
        "current_value": action.get("current_value"),
        "proposed_value": action.get("proposed_value"),
        "deployment_name": action.get("deployment_name"),
        "reason": (state.get("diagnosis") or {}).get("reason"),
        "risk": state.get("risk_level"),
    }

    raw_response = interrupt(payload)
    if not isinstance(raw_response, Mapping):
        raise ValueError("approval resume value must be an object")
    response = ApprovalResponse.model_validate(dict(raw_response))

    trace = [*state.get("node_trace", []), "approval"]
    if response.decision == "reject":
        return {"approval_status": "REJECTED", "node_trace": trace}

    if response.decision == "edit_and_approve":
        if response.proposed_value is None:
            return {
                "approval_status": "BLOCKED",
                "policy_reason": "edit_and_approve requires proposed_value",
                "node_trace": trace,
            }
        action["proposed_value"] = response.proposed_value
        checked = evaluate_action(action)
        if not checked.allowed:
            return {
                "proposed_action": checked.normalized_action,
                "risk_level": checked.risk,
                "policy_reason": checked.reason,
                "approval_status": "BLOCKED",
                "node_trace": trace,
            }
        return {
            "proposed_action": checked.normalized_action,
            "risk_level": checked.risk,
            "policy_reason": checked.reason,
            "approval_status": "APPROVED",
            "node_trace": trace,
        }

    return {"approval_status": "APPROVED", "node_trace": trace}


def route_after_approval(state: IncidentState) -> str:
    status = state.get("approval_status")
    if status == "APPROVED":
        return "approved"
    if status == "REJECTED":
        return "rejected"
    return "blocked"
