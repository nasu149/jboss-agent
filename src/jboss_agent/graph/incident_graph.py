"""STEP 9 end-to-end Incident Response Graph with a bounded recovery loop."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from jboss_agent.config import Settings, get_settings
from jboss_agent.graph.nodes.approval import approval_node, route_after_approval
from jboss_agent.graph.nodes.diagnosis import make_diagnose_node
from jboss_agent.graph.nodes.execution import capture_write_result, prepare_write_call
from jboss_agent.graph.nodes.investigation import (
    make_investigator_node,
    make_route_after_tool_evidence,
    prepare_investigation,
    record_tool_evidence,
    route_after_investigator,
)
from jboss_agent.graph.nodes.risk import route_after_policy, validate_proposed_action
from jboss_agent.graph.nodes.status import blocked, fail_safe, no_action, recovered, rejected
from jboss_agent.graph.nodes.verify import make_recovery_route, make_verify_recovery_node, prepare_retry
from jboss_agent.graph.state import IncidentState
from jboss_agent.llm.incident import build_diagnosis_model, build_investigation_model


def build_step9_graph(
    read_tools: Sequence[Any],
    write_tools: Sequence[Any],
    *,
    checkpointer: Any,
    settings: Settings | None = None,
    investigation_model: Any | None = None,
    diagnosis_model: Any | None = None,
):
    resolved = settings or get_settings()
    investigator = investigation_model or build_investigation_model(resolved, read_tools)
    diagnoser = diagnosis_model or build_diagnosis_model(resolved)

    builder = StateGraph(IncidentState)
    builder.add_node("prepare_investigation", prepare_investigation)
    builder.add_node("investigate", make_investigator_node(investigator))
    builder.add_node("read_tools", ToolNode(list(read_tools)))
    builder.add_node("record_tool_evidence", record_tool_evidence)
    builder.add_node("diagnose", make_diagnose_node(diagnoser))
    builder.add_node("validate_proposed_action", validate_proposed_action)
    builder.add_node("approval", approval_node)
    builder.add_node("prepare_write_call", prepare_write_call)
    builder.add_node("write_tools", ToolNode(list(write_tools)))
    builder.add_node("capture_write_result", capture_write_result)
    builder.add_node("verify_recovery", make_verify_recovery_node(read_tools))
    builder.add_node("prepare_retry", prepare_retry)
    builder.add_node("recovered", recovered)
    builder.add_node("rejected", rejected)
    builder.add_node("blocked", blocked)
    builder.add_node("no_action", no_action)
    builder.add_node("fail_safe", fail_safe)

    builder.add_edge(START, "prepare_investigation")
    builder.add_edge("prepare_investigation", "investigate")
    builder.add_conditional_edges(
        "investigate",
        route_after_investigator,
        {"read_tools": "read_tools", "diagnose": "diagnose"},
    )
    builder.add_edge("read_tools", "record_tool_evidence")
    builder.add_conditional_edges(
        "record_tool_evidence",
        make_route_after_tool_evidence(resolved.max_investigation_rounds),
        {"investigate": "investigate", "diagnose": "diagnose"},
    )
    builder.add_edge("diagnose", "validate_proposed_action")
    builder.add_conditional_edges(
        "validate_proposed_action",
        route_after_policy,
        {"approval": "approval", "blocked": "blocked", "no_action": "no_action"},
    )
    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {"approved": "prepare_write_call", "rejected": "rejected", "blocked": "blocked"},
    )
    builder.add_edge("prepare_write_call", "write_tools")
    builder.add_edge("write_tools", "capture_write_result")
    builder.add_edge("capture_write_result", "verify_recovery")
    builder.add_conditional_edges(
        "verify_recovery",
        make_recovery_route(resolved.max_recovery_attempts),
        {
            "recovered": "recovered",
            "prepare_retry": "prepare_retry",
            "fail_safe": "fail_safe",
        },
    )
    builder.add_edge("prepare_retry", "investigate")

    for terminal in ("recovered", "rejected", "blocked", "no_action", "fail_safe"):
        builder.add_edge(terminal, END)

    return builder.compile(checkpointer=checkpointer)
