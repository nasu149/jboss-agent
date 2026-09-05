"""STEP 8 deterministic preparation and parsing around write MCP ToolNode."""

from __future__ import annotations

import json
import uuid
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from jboss_agent.domain.risk_policy import evaluate_action
from jboss_agent.graph.state import IncidentState


def _write_call_for_action(state: IncidentState) -> tuple[str, dict[str, object]]:
    action = dict(state.get("proposed_action") or {})
    checked = evaluate_action(action)
    if state.get("approval_status") != "APPROVED":
        raise PermissionError("write execution requires approval_status=APPROVED")
    if not checked.allowed or checked.risk == "BLOCKED":
        raise PermissionError(f"write action is blocked: {checked.reason}")

    server_id = state["server_id"]
    action_type = checked.normalized_action.get("type")
    if action_type == "SET_THREAD_POOL_MAX_THREADS":
        return "set_thread_pool_max_threads", {
            "server_id": server_id,
            "value": checked.normalized_action["proposed_value"],
        }
    if action_type == "SET_DATASOURCE_MAX_POOL_SIZE":
        return "set_datasource_max_pool_size", {
            "server_id": server_id,
            "value": checked.normalized_action["proposed_value"],
        }
    if action_type == "RESTART_DEPLOYMENT":
        return "restart_deployment", {
            "server_id": server_id,
            "deployment_name": checked.normalized_action["deployment_name"],
        }
    if action_type == "RELOAD_SERVER":
        return "reload_server", {"server_id": server_id}
    raise ValueError(f"action does not map to a write MCP tool: {action_type}")


def prepare_write_call(state: IncidentState) -> dict[str, object]:
    """Translate a validated approved action to one explicit MCP Tool call.

    No LLM chooses the write tool. This is the safety boundary introduced in
    STEP 8: LangGraph/Python performs the deterministic mapping after approval.
    """

    tool_name, args = _write_call_for_action(state)
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": tool_name,
                "args": args,
                "id": f"write-{uuid.uuid4().hex[:12]}",
                "type": "tool_call",
            }
        ],
    )
    return {
        "messages": [message],
        "node_trace": [*state.get("node_trace", []), "prepare_write_call"],
    }


def _normalize_content(content: Any) -> Any:
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content
    if isinstance(content, list) and len(content) == 1 and isinstance(content[0], dict):
        block = content[0]
        if "text" in block and isinstance(block["text"], str):
            return _normalize_content(block["text"])
    return content


def capture_write_result(state: IncidentState) -> dict[str, object]:
    messages = state.get("messages", [])
    if not messages or not isinstance(messages[-1], ToolMessage):
        raise RuntimeError("write ToolNode did not produce a ToolMessage")
    message = messages[-1]
    result = {
        "tool_name": message.name,
        "tool_call_id": message.tool_call_id,
        "content": _normalize_content(message.content),
    }
    return {
        "execution_result": result,
        "recovery_attempts": state.get("recovery_attempts", 0) + 1,
        "node_trace": [*state.get("node_trace", []), "capture_write_result"],
    }
