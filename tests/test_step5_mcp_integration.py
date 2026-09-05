from __future__ import annotations

import pytest
from langchain_core.messages import ToolMessage

from jboss_agent.graph.mcp_demo_graph import build_step5_graph
from jboss_agent.mcp_client.client import load_fake_jboss_read_tools
from jboss_agent.mcp_client.tool_registry import READ_ONLY_JBOSS_TOOL_NAMES


@pytest.mark.asyncio
async def test_step5_discovers_and_executes_fake_jboss_mcp_tool() -> None:
    _client, tools = await load_fake_jboss_read_tools()
    assert {tool.name for tool in tools} == READ_ONLY_JBOSS_TOOL_NAMES

    graph = build_step5_graph(tools, tool_name="get_server_health")
    result = await graph.ainvoke({"server_id": "jboss-01", "messages": []})

    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 1
    assert "UP" in str(tool_messages[0].content)
