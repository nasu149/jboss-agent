"""LangGraph State definitions through STEP 5."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from jboss_agent.domain.models import IncidentCategory


class CoreLearningState(TypedDict, total=False):
    """Minimal state used by STEP 1."""

    input_log_lines: list[str]
    log_text: str
    simple_check_result: str
    node_trace: list[str]


class MonitoringState(CoreLearningState, total=False):
    """STEP 2 state extended with the structured LLM classification."""

    incident_detected: bool
    category: IncidentCategory
    confidence: float
    summary: str
    evidence: list[str]
    route_taken: str


class CursorMonitoringState(MonitoringState, total=False):
    """STEP 3 state for incremental log monitoring.

    ``previous_log_cursor`` is input for a run; ``current_log_cursor`` is the
    value the caller should persist/pass to the next run. STEP 7 introduces a
    real LangGraph checkpointer; STEP 3 intentionally keeps the mechanism
    visible by passing the cursor explicitly.
    """

    server_id: str
    previous_log_cursor: int
    current_log_cursor: int
    new_log_lines: list[str]
    has_new_logs: bool


class TeamsNotificationState(CursorMonitoringState, total=False):
    """STEP 4 state with LangGraph's message reducer for ToolNode interaction."""

    messages: Annotated[list[AnyMessage], add_messages]
    incident_id: str
    severity: str
    teams_notified: bool
    teams_tool_status: str
    teams_tool_result: dict[str, Any]


class MCPDemoState(TypedDict, total=False):
    """Small STEP 5 state used to execute an MCP-derived LangChain tool."""

    messages: Annotated[list[AnyMessage], add_messages]
    server_id: str
    requested_tool: str
