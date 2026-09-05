from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from jboss_agent.graph.approval_graph import build_step7_graph


def _initial() -> dict[str, object]:
    return {
        "incident_id": "inc-7",
        "server_id": "jboss-test",
        "diagnosis": {"reason": "configuration regression"},
        "proposed_action": {
            "type": "SET_THREAD_POOL_MAX_THREADS",
            "current_value": 20,
            "proposed_value": 80,
            "deployment_name": None,
            "rationale": "restore capacity",
        },
        "messages": [],
        "node_trace": [],
    }


def test_step7_interrupts_and_resumes_same_thread() -> None:
    graph = build_step7_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "incident:step7"}}
    paused = graph.invoke(_initial(), config=config)
    assert paused["__interrupt__"][0].value["action"] == "SET_THREAD_POOL_MAX_THREADS"

    resumed = graph.invoke(Command(resume={"decision": "approve"}), config=config)
    assert resumed["approval_status"] == "APPROVED"
    assert resumed["node_trace"][-1] == "approved_ready"


def test_step7_invalid_human_edit_is_blocked() -> None:
    graph = build_step7_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "incident:step7-edit"}}
    graph.invoke(_initial(), config=config)
    result = graph.invoke(
        Command(resume={"decision": "edit_and_approve", "proposed_value": 999}),
        config=config,
    )
    assert result["approval_status"] == "BLOCKED"
