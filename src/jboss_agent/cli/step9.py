"""CLI runner for STEP 9 end-to-end investigation -> HITL -> write -> verify loop."""

from __future__ import annotations

import asyncio
import json
import uuid

from langgraph.types import Command

from jboss_agent.config import get_settings
from jboss_agent.graph.incident_graph import build_step9_graph
from jboss_agent.jboss.fake_operations import FakeJBossOperations
from jboss_agent.mcp_client.client import load_fake_jboss_read_write_tools
from jboss_agent.persistence.checkpointer import open_checkpointer
from jboss_agent.simulator.demo_scenarios import seed_thread_pool_configuration_incident


async def _run() -> None:
    settings = get_settings()
    fake = FakeJBossOperations(settings.fake_jboss_data_dir, server_id=settings.server_id)
    logs = seed_thread_pool_configuration_incident(fake)
    _client, read_tools, write_tools = await load_fake_jboss_read_write_tools()

    incident_id = f"inc-{uuid.uuid4().hex[:8]}"
    thread_id = f"incident:{incident_id}"
    config = {"configurable": {"thread_id": thread_id}}
    initial = {
        "incident_id": incident_id,
        "server_id": settings.server_id,
        "category": "UNKNOWN",
        "severity": "HIGH",
        "confidence": 0.7,
        "initial_log_lines": logs,
        "messages": [],
        "evidence": [],
        "investigation_count": 0,
        "recovery_attempts": 0,
        "node_trace": [],
    }

    async with open_checkpointer(settings) as checkpointer:
        graph = build_step9_graph(
            read_tools,
            write_tools,
            checkpointer=checkpointer,
            settings=settings,
        )
        result = await graph.ainvoke(initial, config=config)

        approval_number = 0
        while result.get("__interrupt__"):
            approval_number += 1
            interrupt_info = result["__interrupt__"][0]
            print(f"\n--- APPROVAL #{approval_number} / thread_id={thread_id} ---")
            print(json.dumps(interrupt_info.value, ensure_ascii=False, indent=2, default=str))
            print("Demo CLI decision: APPROVE")
            result = await graph.ainvoke(
                Command(resume={"decision": "approve"}),
                config=config,
            )

    print("\nSTEP 9 final state")
    print(
        json.dumps(
            {
                "incident_id": incident_id,
                "thread_id": thread_id,
                "recovered": result.get("recovered"),
                "recovery_attempts": result.get("recovery_attempts"),
                "diagnosis": result.get("diagnosis"),
                "proposed_action": result.get("proposed_action"),
                "approval_status": result.get("approval_status"),
                "execution_result": result.get("execution_result"),
                "failure_reason": result.get("failure_reason"),
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
