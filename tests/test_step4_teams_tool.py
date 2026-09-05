from __future__ import annotations

import json

from langchain_core.messages import AIMessage, BaseMessage

from jboss_agent.config import get_settings
from jboss_agent.graph.teams_tool_graph import build_step4_graph
from jboss_agent.local_tools.teams import reset_delivery_registry_for_tests, send_teams_alert


class ForcedTeamsToolModel:
    def invoke(self, input: object) -> BaseMessage:  # noqa: A002
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "send_teams_alert",
                    "args": {
                        "server_id": "jboss-test",
                        "incident_id": "inc-step4",
                        "severity": "HIGH",
                        "category": "THREAD_POOL",
                        "confidence": 0.91,
                        "summary": "worker saturation suspected",
                    },
                    "id": "teams-call-1",
                    "type": "tool_call",
                }
            ],
        )


class FinalMessageModel:
    def invoke(self, input: object) -> BaseMessage:  # noqa: A002
        return AIMessage(content="Teams notification completed.")


def _configure_dry_run(monkeypatch) -> None:
    monkeypatch.setenv("TEAMS_DRY_RUN", "true")
    monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)
    get_settings.cache_clear()
    reset_delivery_registry_for_tests()


def test_step4_toolnode_executes_local_teams_tool_in_dry_run(monkeypatch) -> None:
    _configure_dry_run(monkeypatch)
    graph = build_step4_graph(
        tool_calling_model=ForcedTeamsToolModel(),
        final_model=FinalMessageModel(),
    )

    result = graph.invoke(
        {
            "server_id": "jboss-test",
            "incident_id": "inc-step4",
            "incident_detected": True,
            "severity": "HIGH",
            "category": "THREAD_POOL",
            "confidence": 0.91,
            "summary": "worker saturation suspected",
            "teams_notified": False,
        }
    )

    assert result["teams_notified"] is True
    assert result["teams_tool_status"] == "dry_run"
    assert result["node_trace"] == [
        "notification_guard",
        "prepare_teams_request",
        "call_teams_tool",
        "finalize_teams",
    ]


def test_teams_tool_duplicate_call_is_idempotent(monkeypatch) -> None:
    _configure_dry_run(monkeypatch)
    args = {
        "server_id": "jboss-test",
        "incident_id": "inc-duplicate",
        "severity": "HIGH",
        "category": "THREAD_POOL",
        "confidence": 0.9,
        "summary": "test",
    }

    first = json.loads(send_teams_alert.invoke(args))
    second = json.loads(send_teams_alert.invoke(args))

    assert first["status"] == "dry_run"
    assert second["status"] == "duplicate_skipped"
