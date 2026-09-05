from __future__ import annotations

from langchain.tools import tool

from jboss_agent.graph.write_execution_graph import build_step8_graph


@tool
def set_thread_pool_max_threads(server_id: str, value: int) -> dict[str, object]:
    """Set max thread count after approval."""
    return {"server_id": server_id, "value": value, "success": True}


def test_step8_executes_approved_explicit_write_tool() -> None:
    graph = build_step8_graph([set_thread_pool_max_threads])
    result = graph.invoke(
        {
            "incident_id": "inc-8",
            "server_id": "jboss-test",
            "approval_status": "APPROVED",
            "proposed_action": {
                "type": "SET_THREAD_POOL_MAX_THREADS",
                "current_value": 20,
                "proposed_value": 80,
                "rationale": "restore capacity",
            },
            "messages": [],
            "recovery_attempts": 0,
            "node_trace": [],
        }
    )
    assert result["execution_result"]["tool_name"] == "set_thread_pool_max_threads"
    assert result["recovery_attempts"] == 1
