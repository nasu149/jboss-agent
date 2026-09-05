"""STEP 6: read-only MCP investigation selected by Gemini."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from jboss_agent.config import Settings, get_settings
from jboss_agent.graph.nodes.diagnosis import make_diagnose_node
from jboss_agent.graph.nodes.investigation import (
    make_investigator_node,
    make_route_after_tool_evidence,
    prepare_investigation,
    record_tool_evidence,
    route_after_investigator,
)
from jboss_agent.graph.state import IncidentState
from jboss_agent.llm.incident import build_diagnosis_model, build_investigation_model


def build_step6_graph(
    read_tools: Sequence[Any],
    *,
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

    builder.add_edge(START, "prepare_investigation")
    builder.add_edge("prepare_investigation", "investigate")
    builder.add_conditional_edges("investigate", route_after_investigator)
    builder.add_edge("read_tools", "record_tool_evidence")
    builder.add_conditional_edges(
        "record_tool_evidence",
        make_route_after_tool_evidence(resolved.max_investigation_rounds),
    )
    builder.add_edge("diagnose", END)
    return builder.compile()
