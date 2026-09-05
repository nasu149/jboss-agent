"""CLI runner for STEP 6 agentic read-only investigation."""

from __future__ import annotations

import asyncio
import json
import uuid

from langchain_core.messages import AIMessage, ToolMessage

from jboss_agent.config import get_settings
from jboss_agent.graph.agentic_investigation_graph import build_step6_graph
from jboss_agent.jboss.fake_operations import FakeJBossOperations
from jboss_agent.mcp_client.client import load_fake_jboss_read_tools
from jboss_agent.simulator.demo_scenarios import seed_thread_pool_configuration_incident


async def _run() -> None:
    settings = get_settings()
    fake = FakeJBossOperations(settings.fake_jboss_data_dir, server_id=settings.server_id)
    logs = seed_thread_pool_configuration_incident(fake)
    _client, read_tools = await load_fake_jboss_read_tools()
    graph = build_step6_graph(read_tools, settings=settings)
    incident_id = f"inc-{uuid.uuid4().hex[:8]}"
    result = await graph.ainvoke(
        {
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
        }
    )

    tool_calls: list[str] = []
    tool_results: list[str] = []
    for message in result.get("messages", []):
        if isinstance(message, AIMessage):
            tool_calls.extend(call["name"] for call in message.tool_calls)
        elif isinstance(message, ToolMessage):
            tool_results.append(message.name or "unknown")

    print("STEP 6: Gemini selects READ-ONLY MCP tools; write tools are not bound to the model")
    print(
        json.dumps(
            {
                "incident_id": incident_id,
                "investigation_rounds": result.get("investigation_count"),
                "llm_selected_tools": tool_calls,
                "tool_results": tool_results,
                "diagnosis": result.get("diagnosis"),
                "proposed_action": result.get("proposed_action"),
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
