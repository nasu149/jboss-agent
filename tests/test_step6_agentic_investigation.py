from __future__ import annotations

from langchain.tools import tool
from langchain_core.messages import AIMessage

from jboss_agent.graph.agentic_investigation_graph import build_step6_graph


@tool
def get_thread_pool_status(server_id: str) -> dict[str, object]:
    """Read thread-pool status."""
    return {"server_id": server_id, "max_threads": 20, "active_threads": 20, "queue_size": 9}


class InvestigationModel:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, input: object) -> AIMessage:  # noqa: A002
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_thread_pool_status",
                        "args": {"server_id": "jboss-test"},
                        "id": "read-1",
                        "type": "tool_call",
                    }
                ],
            )
        return AIMessage(content="Thread pool saturation is sufficiently evidenced.")


class DiagnosisModel:
    def invoke(self, input: str) -> object:  # noqa: A002
        return {
            "root_cause": "THREAD_POOL_CONFIGURATION",
            "confidence": 0.95,
            "reason": "max_threads is saturated",
            "recommended_action": {
                "type": "SET_THREAD_POOL_MAX_THREADS",
                "current_value": 20,
                "proposed_value": 80,
                "deployment_name": None,
                "rationale": "restore capacity",
            },
        }


def test_step6_llm_selects_read_tool_then_diagnoses() -> None:
    model = InvestigationModel()
    graph = build_step6_graph(
        [get_thread_pool_status],
        investigation_model=model,
        diagnosis_model=DiagnosisModel(),
    )
    result = graph.invoke(
        {
            "incident_id": "inc-6",
            "server_id": "jboss-test",
            "category": "UNKNOWN",
            "severity": "HIGH",
            "initial_log_lines": ["task rejected"],
            "messages": [],
            "evidence": [],
            "investigation_count": 0,
            "recovery_attempts": 0,
        }
    )
    assert model.calls == 2
    assert result["evidence"][0]["tool_name"] == "get_thread_pool_status"
    assert result["diagnosis"]["root_cause"] == "THREAD_POOL_CONFIGURATION"
