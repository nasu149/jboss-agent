"""LangGraph State definitions through STEP 9."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages

from jboss_agent.domain.models import IncidentCategory


class CoreLearningState(TypedDict, total=False):
    input_log_lines: list[str]
    log_text: str
    simple_check_result: str
    node_trace: list[str]


class MonitoringState(CoreLearningState, total=False):
    incident_detected: bool
    category: IncidentCategory
    confidence: float
    summary: str
    evidence: list[str]
    route_taken: str


class CursorMonitoringState(MonitoringState, total=False):
    server_id: str
    previous_log_cursor: int
    current_log_cursor: int
    new_log_lines: list[str]
    has_new_logs: bool


class TeamsNotificationState(CursorMonitoringState, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    incident_id: str
    severity: str
    teams_notified: bool
    teams_tool_status: str
    teams_tool_result: dict[str, Any]


class MCPDemoState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    server_id: str
    requested_tool: str


class IncidentState(MessagesState, total=False):
    """State for STEP 6-9 Incident Response Graph.

    Inheriting ``MessagesState`` makes the message reducer explicit: each LLM and
    ToolNode update appends/merges messages rather than replacing the list.
    """

    incident_id: str
    server_id: str
    category: str
    severity: str
    confidence: float
    initial_log_lines: list[str]
    evidence: list[dict[str, Any]]
    investigation_count: int
    diagnosis: dict[str, Any] | None
    proposed_action: dict[str, Any] | None
    risk_level: str | None
    policy_reason: str | None
    approval_status: str | None
    execution_result: dict[str, Any] | None
    recovered: bool | None
    recovery_attempts: int
    failure_reason: str | None
    node_trace: list[str]
