"""STEP 10 durable Monitoring Graph used by Scheduler/UI/Evaluation.

Earlier step graphs remain untouched for learning. This graph connects cursor
monitoring, Gemini classification, incident creation, and the local Teams Tool.
The scheduler is deliberately outside this module.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from jboss_agent.config import Settings, get_settings
from jboss_agent.graph.nodes.analyze_logs import make_analyze_logs_node
from jboss_agent.graph.state import OperationalMonitoringState
from jboss_agent.llm.log_classifier import LogClassifier, build_log_classifier
from jboss_agent.local_tools.teams import send_teams_alert
from jboss_agent.mcp_client.results import normalize_tool_result


def _reset_cycle(state: OperationalMonitoringState) -> dict[str, object]:
    return {
        "new_log_lines": [],
        "has_new_logs": False,
        "incident_detected": False,
        "category": "NORMAL",
        "confidence": 0.0,
        "summary": "No new logs",
        "evidence": [],
        "incident_id": None,
        "severity": "LOW",
        "teams_notified": False,
        "teams_tool_status": None,
        "teams_tool_result": None,
        "node_trace": ["start_monitoring_cycle"],
    }


def _find_tool(tools: Sequence[Any], name: str) -> Any:
    for tool in tools:
        if tool.name == name:
            return tool
    raise ValueError(f"required MCP tool not found: {name}")


def make_collect_logs_mcp_node(read_tools: Sequence[Any]):
    read_log = _find_tool(read_tools, "read_server_log")

    async def collect(state: OperationalMonitoringState) -> dict[str, object]:
        server_id = state["server_id"]
        previous = int(state.get("previous_log_cursor", 0))
        cursor_reset = False
        try:
            raw = await read_log.ainvoke({"server_id": server_id, "cursor": previous})
        except Exception as exc:
            # Demo/evaluation may reset the fake log. Treat the known cursor-beyond-EOF
            # condition like log rotation and deterministically restart from byte 0.
            text = str(exc).lower()
            if previous <= 0 or "beyond current log size" not in text:
                raise
            previous = 0
            cursor_reset = True
            raw = await read_log.ainvoke({"server_id": server_id, "cursor": 0})
        result = normalize_tool_result(raw)
        lines = [str(line) for line in result.get("lines", [])]
        current = int(result.get("to_cursor", previous))
        return {
            "scan_from_cursor": previous,
            "cursor_reset_detected": cursor_reset,
            "current_log_cursor": current,
            "new_log_lines": lines,
            "log_text": "\n".join(lines),
            "has_new_logs": bool(lines),
            "node_trace": [*state.get("node_trace", []), "collect_logs_mcp"],
        }

    return collect


def route_on_delta(state: OperationalMonitoringState) -> str:
    return "analyze" if state.get("has_new_logs") else "commit"


def route_after_analysis(state: OperationalMonitoringState) -> str:
    return "incident" if state.get("incident_detected") else "commit"


def _create_incident(state: OperationalMonitoringState) -> dict[str, object]:
    confidence = float(state.get("confidence", 0.0))
    category = str(state.get("category", "UNKNOWN"))
    if category == "UNKNOWN":
        severity = "MEDIUM"
    elif confidence >= 0.85:
        severity = "HIGH"
    else:
        severity = "MEDIUM"
    return {
        "incident_id": f"inc-{uuid.uuid4().hex[:10]}",
        "severity": severity,
        "node_trace": [*state.get("node_trace", []), "create_incident"],
    }


def make_notify_teams_node(notifier: Callable[[dict[str, object]], object] | None = None):
    resolved_notifier = notifier or send_teams_alert.invoke

    def notify(state: OperationalMonitoringState) -> dict[str, object]:
        result_raw = resolved_notifier(
            {
                "server_id": state["server_id"],
                "incident_id": state["incident_id"],
                "severity": state["severity"],
                "category": state["category"],
                "confidence": state["confidence"],
                "summary": state["summary"],
            }
        )
        if isinstance(result_raw, dict):
            result = result_raw
        else:
            try:
                result = json.loads(str(result_raw))
            except json.JSONDecodeError:
                result = {"success": False, "status": "invalid_tool_result", "raw": str(result_raw)}
        return {
            "teams_notified": bool(result.get("success")),
            "teams_tool_status": str(result.get("status", "unknown")),
            "teams_tool_result": result,
            "node_trace": [*state.get("node_trace", []), "notify_teams_local_tool"],
        }

    return notify


def _commit_cursor(state: OperationalMonitoringState) -> dict[str, object]:
    current = int(state.get("current_log_cursor", state.get("previous_log_cursor", 0)))
    return {
        "previous_log_cursor": current,
        "node_trace": [*state.get("node_trace", []), "commit_cursor"],
    }


def build_operational_monitoring_graph(
    read_tools: Sequence[Any],
    *,
    checkpointer: Any,
    settings: Settings | None = None,
    classifier: LogClassifier | None = None,
    notifier: Callable[[dict[str, object]], object] | None = None,
):
    resolved = settings or get_settings()
    resolved_classifier = classifier or build_log_classifier(resolved)

    builder = StateGraph(OperationalMonitoringState)
    builder.add_node("start_monitoring_cycle", _reset_cycle)
    builder.add_node("collect_logs", make_collect_logs_mcp_node(read_tools))
    builder.add_node("analyze_logs", make_analyze_logs_node(resolved_classifier))
    builder.add_node("create_incident", _create_incident)
    builder.add_node("notify_teams", make_notify_teams_node(notifier))
    builder.add_node("commit_cursor", _commit_cursor)

    builder.add_edge(START, "start_monitoring_cycle")
    builder.add_edge("start_monitoring_cycle", "collect_logs")
    builder.add_conditional_edges(
        "collect_logs", route_on_delta, {"analyze": "analyze_logs", "commit": "commit_cursor"}
    )
    builder.add_conditional_edges(
        "analyze_logs", route_after_analysis, {"incident": "create_incident", "commit": "commit_cursor"}
    )
    builder.add_edge("create_incident", "notify_teams")
    builder.add_edge("notify_teams", "commit_cursor")
    builder.add_edge("commit_cursor", END)

    return builder.compile(checkpointer=checkpointer)
