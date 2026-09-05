from __future__ import annotations

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from jboss_agent.graph.approval_graph import build_step7_graph


@pytest.mark.asyncio
async def test_pending_approval_survives_sqlite_checkpointer_reopen(tmp_path) -> None:
    db = tmp_path / "checkpoints.sqlite"
    config = {"configurable": {"thread_id": "incident:durable"}}
    initial = {
        "incident_id": "durable",
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

    async with AsyncSqliteSaver.from_conn_string(str(db)) as saver:
        graph = build_step7_graph(checkpointer=saver)
        paused = await graph.ainvoke(initial, config=config)
        assert paused["__interrupt__"]

    async with AsyncSqliteSaver.from_conn_string(str(db)) as saver:
        graph = build_step7_graph(checkpointer=saver)
        resumed = await graph.ainvoke(Command(resume={"decision": "approve"}), config=config)
        assert resumed["approval_status"] == "APPROVED"
