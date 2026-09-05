"""CLI runner for STEP 5 Fake JBoss MCP Server/Client integration."""

from __future__ import annotations

import asyncio
import json

from langchain_core.messages import ToolMessage

from jboss_agent.config import get_settings
from jboss_agent.graph.mcp_demo_graph import build_step5_graph
from jboss_agent.jboss.fake_operations import FakeJBossOperations
from jboss_agent.mcp_client.client import load_fake_jboss_read_tools


async def _run() -> None:
    settings = get_settings()
    fake = FakeJBossOperations(settings.fake_jboss_data_dir, server_id=settings.server_id)
    fake.ensure_initialized()

    _client, tools = await load_fake_jboss_read_tools()
    names = sorted(tool.name for tool in tools)
    print("Discovered MCP read tools:")
    for name in names:
        print(f"  - {name}")

    graph = build_step5_graph(tools, tool_name="get_server_health")
    result = await graph.ainvoke({"server_id": settings.server_id, "messages": []})
    tool_messages = [
        message for message in result.get("messages", []) if isinstance(message, ToolMessage)
    ]

    print("\nSTEP 5 graph: Python emits tool_call -> ToolNode -> MCP stdio server -> ToolMessage")
    print(f"requested_tool={result.get('requested_tool')}")
    for message in tool_messages:
        content = message.content
        if isinstance(content, str):
            print(content)
        else:
            print(json.dumps(content, ensure_ascii=False, indent=2, default=str))



def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
