"""CLI runner for STEP 8 approved MCP write execution."""

from __future__ import annotations

import asyncio
import json

from jboss_agent.config import get_settings
from jboss_agent.graph.write_execution_graph import build_step8_graph
from jboss_agent.jboss.fake_operations import FakeJBossOperations
from jboss_agent.mcp_client.client import load_fake_jboss_write_tools


async def _run() -> None:
    settings = get_settings()
    fake = FakeJBossOperations(settings.fake_jboss_data_dir, server_id=settings.server_id)
    fake.reset(include_boot_logs=False)
    fake.set_thread_pool_max_threads(settings.server_id, 20)
    fake.simulate_thread_pool_load(active_threads=20, queue_size=9, rejected_tasks=3)

    _client, write_tools = await load_fake_jboss_write_tools()
    graph = build_step8_graph(write_tools)
    result = await graph.ainvoke(
        {
            "incident_id": "inc-step8-demo",
            "server_id": settings.server_id,
            "approval_status": "APPROVED",
            "risk_level": "MEDIUM",
            "proposed_action": {
                "type": "SET_THREAD_POOL_MAX_THREADS",
                "current_value": 20,
                "proposed_value": 80,
                "deployment_name": None,
                "rationale": "restore previous capacity",
            },
            "messages": [],
            "recovery_attempts": 0,
            "node_trace": [],
        }
    )
    after = fake.get_thread_pool_status(settings.server_id)
    print("STEP 8: Python maps an APPROVED action to one explicit write MCP Tool")
    print(
        json.dumps(
            {
                "execution_result": result.get("execution_result"),
                "thread_pool_after": after,
                "node_trace": result.get("node_trace"),
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
