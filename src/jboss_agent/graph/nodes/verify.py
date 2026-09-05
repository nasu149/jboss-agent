"""STEP 9 deterministic post-change verification and recovery routing."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import HumanMessage

from jboss_agent.graph.state import IncidentState


def _tool_map(tools: Sequence[Any]) -> dict[str, Any]:
    return {tool.name: tool for tool in tools}


def _normalize_result(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"raw": value}
    if hasattr(value, "content"):
        return _normalize_result(value.content)
    return {"raw": value}


def make_verify_recovery_node(read_tools: Sequence[Any]):
    tools = _tool_map(read_tools)

    async def verify(state: IncidentState) -> dict[str, object]:
        server_id = state["server_id"]
        action_type = (state.get("proposed_action") or {}).get("type")
        health = _normalize_result(
            await tools["get_server_health"].ainvoke({"server_id": server_id})
        )
        details: dict[str, Any] = {"health": health}
        healthy = health.get("status") == "UP" and float(health.get("request_error_rate", 1.0)) < 0.05

        if action_type == "SET_THREAD_POOL_MAX_THREADS":
            pool = _normalize_result(
                await tools["get_thread_pool_status"].ainvoke({"server_id": server_id})
            )
            details["thread_pool"] = pool
            healthy = healthy and int(pool.get("active_threads", 10**9)) <= int(
                pool.get("max_threads", -1)
            )
            healthy = healthy and int(pool.get("queue_size", 1)) == 0
            healthy = healthy and int(pool.get("rejected_tasks", 1)) == 0
        elif action_type == "SET_DATASOURCE_MAX_POOL_SIZE":
            ds = _normalize_result(
                await tools["get_datasource_status"].ainvoke({"server_id": server_id})
            )
            details["datasource"] = ds
            healthy = healthy and int(ds.get("active_count", 10**9)) <= int(
                ds.get("max_pool_size", -1)
            )
            healthy = healthy and int(ds.get("timed_out_requests", 1)) == 0
        elif action_type == "RESTART_DEPLOYMENT":
            deployment = _normalize_result(
                await tools["get_deployment_status"].ainvoke({"server_id": server_id})
            )
            details["deployment"] = deployment
            healthy = healthy and deployment.get("status") == "OK" and bool(
                deployment.get("enabled")
            )
        elif action_type == "RELOAD_SERVER":
            pass

        evidence = [*state.get("evidence", [])]
        evidence.append({"tool_name": "recovery_verification", "content": details})
        return {
            "recovered": healthy,
            "evidence": evidence,
            "node_trace": [*state.get("node_trace", []), "verify_recovery"],
        }

    return verify


def make_recovery_route(max_attempts: int):
    def route(state: IncidentState) -> str:
        if state.get("recovered") is True:
            return "recovered"
        if state.get("recovery_attempts", 0) >= max_attempts:
            return "fail_safe"
        return "prepare_retry"

    return route


def prepare_retry(state: IncidentState) -> dict[str, object]:
    """Loop back with history retained, but reset per-investigation counters."""
    return {
        "messages": [
            HumanMessage(
                content=(
                    "The approved remediation did not recover the server. "
                    "Re-investigate using read-only tools and challenge the previous diagnosis."
                )
            )
        ],
        "investigation_count": 0,
        "diagnosis": None,
        "proposed_action": None,
        "risk_level": None,
        "policy_reason": None,
        "approval_status": None,
        "execution_result": None,
        "recovered": None,
        "node_trace": [*state.get("node_trace", []), "prepare_retry"],
    }
