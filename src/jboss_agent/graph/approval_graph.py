"""STEP 7: risk validation + interrupt()/Command(resume=...) learning graph."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from jboss_agent.graph.nodes.approval import approval_node, route_after_approval
from jboss_agent.graph.nodes.risk import route_after_policy, validate_proposed_action
from jboss_agent.graph.nodes.status import approved_ready, blocked, no_action, rejected
from jboss_agent.graph.state import IncidentState


def build_step7_graph(*, checkpointer: Any):
    builder = StateGraph(IncidentState)
    builder.add_node("validate_proposed_action", validate_proposed_action)
    builder.add_node("approval", approval_node)
    builder.add_node("approved_ready", approved_ready)
    builder.add_node("rejected", rejected)
    builder.add_node("blocked", blocked)
    builder.add_node("no_action", no_action)

    builder.add_edge(START, "validate_proposed_action")
    builder.add_conditional_edges("validate_proposed_action", route_after_policy)
    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {"approved": "approved_ready", "rejected": "rejected", "blocked": "blocked"},
    )
    builder.add_edge("approved_ready", END)
    builder.add_edge("rejected", END)
    builder.add_edge("blocked", END)
    builder.add_edge("no_action", END)
    return builder.compile(checkpointer=checkpointer)
