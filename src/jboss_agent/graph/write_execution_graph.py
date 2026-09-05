"""STEP 8: execute only an already-approved validated MCP write action."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from jboss_agent.graph.nodes.execution import capture_write_result, prepare_write_call
from jboss_agent.graph.state import IncidentState


def build_step8_graph(write_tools: Sequence[Any]):
    builder = StateGraph(IncidentState)
    builder.add_node("prepare_write_call", prepare_write_call)
    builder.add_node("write_tools", ToolNode(list(write_tools)))
    builder.add_node("capture_write_result", capture_write_result)

    builder.add_edge(START, "prepare_write_call")
    builder.add_edge("prepare_write_call", "write_tools")
    builder.add_edge("write_tools", "capture_write_result")
    builder.add_edge("capture_write_result", END)
    return builder.compile()
