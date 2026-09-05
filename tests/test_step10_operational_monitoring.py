from __future__ import annotations

import json

import pytest
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from jboss_agent.graph.operational_monitoring_graph import build_operational_monitoring_graph


class FakeClassifier:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, input: str) -> object:  # noqa: A002
        self.calls += 1
        return {
            "incident_detected": False,
            "category": "NORMAL",
            "confidence": 0.99,
            "summary": "normal activity",
            "evidence": ["INFO only"],
        }


class LogSource:
    def __init__(self) -> None:
        self.lines = ["2026-09-05 INFO request completed"]

    def read(self, cursor: int) -> dict[str, object]:
        payload = "\n".join(self.lines) + ("\n" if self.lines else "")
        raw = payload.encode()
        return {
            "from_cursor": cursor,
            "to_cursor": len(raw),
            "lines": raw[cursor:].decode().splitlines(),
        }


@pytest.mark.asyncio
async def test_fixed_monitor_thread_persists_cursor_and_skips_llm_without_delta() -> None:
    source = LogSource()

    @tool
    def read_server_log(server_id: str, cursor: int) -> dict[str, object]:
        """Read fake log delta."""
        return source.read(cursor)

    classifier = FakeClassifier()
    graph = build_operational_monitoring_graph(
        [read_server_log],
        checkpointer=InMemorySaver(),
        classifier=classifier,
        notifier=lambda payload: json.dumps({"success": True, "status": "test"}),
    )
    config = {"configurable": {"thread_id": "monitor:jboss-test"}}

    first = await graph.ainvoke({"server_id": "jboss-test"}, config=config)
    second = await graph.ainvoke({"server_id": "jboss-test"}, config=config)

    assert first["has_new_logs"] is True
    assert second["has_new_logs"] is False
    assert second["scan_from_cursor"] == first["current_log_cursor"]
    assert classifier.calls == 1
