"""Structured diagnosis prompt assembled after the tool loop."""

from __future__ import annotations

from jboss_agent.graph.state import IncidentState


DIAGNOSIS_INSTRUCTIONS = """Produce a structured JBoss incident diagnosis using only the supplied
initial logs and tool evidence. The recommended_action must be one of the schema
options. If evidence does not justify a safe action, use type=NONE. For a recent
configuration regression, prefer restoring the clearly observed previous value.
Do not fabricate current_value, proposed_value, or deployment_name.
"""


def build_diagnosis_prompt(state: IncidentState) -> str:
    evidence_lines = []
    for item in state.get("evidence", []):
        evidence_lines.append(f"- {item.get('tool_name')}: {item.get('content')}")
    evidence = "\n".join(evidence_lines) or "- No tool evidence captured"
    logs = "\n".join(state.get("initial_log_lines", [])) or "(none)"
    return (
        f"{DIAGNOSIS_INSTRUCTIONS}\n\n"
        f"Server: {state['server_id']}\n"
        f"Initial category: {state.get('category', 'UNKNOWN')}\n"
        f"Initial logs:\n{logs}\n\n"
        f"Read-only tool evidence:\n{evidence}"
    )
