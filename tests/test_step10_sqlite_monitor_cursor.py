from __future__ import annotations

import json

import pytest
from langchain.tools import tool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

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


@pytest.mark.asyncio
async def test_monitor_cursor_survives_sqlite_reopen(tmp_path) -> None:
    payload = b"2026-09-05 INFO request completed\n"

    @tool
    def read_server_log(server_id: str, cursor: int) -> dict[str, object]:
        """Read bytes after a cursor."""
        return {
            "server_id": server_id,
            "from_cursor": cursor,
            "to_cursor": len(payload),
            "lines": payload[cursor:].decode().splitlines(),
        }

    db = tmp_path / "checkpoints.sqlite"
    config = {"configurable": {"thread_id": "monitor:jboss-test"}}
    first_classifier = FakeClassifier()

    async with AsyncSqliteSaver.from_conn_string(str(db)) as saver:
        await saver.setup()
        graph = build_operational_monitoring_graph(
            [read_server_log],
            checkpointer=saver,
            classifier=first_classifier,
            notifier=lambda data: json.dumps({"success": True, "status": "test"}),
        )
        first = await graph.ainvoke({"server_id": "jboss-test"}, config=config)
        assert first["current_log_cursor"] == len(payload)
        assert first_classifier.calls == 1

    second_classifier = FakeClassifier()
    async with AsyncSqliteSaver.from_conn_string(str(db)) as saver:
        await saver.setup()
        graph = build_operational_monitoring_graph(
            [read_server_log],
            checkpointer=saver,
            classifier=second_classifier,
            notifier=lambda data: json.dumps({"success": True, "status": "test"}),
        )
        second = await graph.ainvoke({"server_id": "jboss-test"}, config=config)
        assert second["scan_from_cursor"] == len(payload)
        assert second["has_new_logs"] is False
        assert second_classifier.calls == 0
