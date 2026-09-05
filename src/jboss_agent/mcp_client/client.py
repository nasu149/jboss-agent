"""STEP 5 LangChain adapter for the local Fake JBoss MCP Server."""

from __future__ import annotations

import sys
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from jboss_agent.mcp_client.tool_registry import validate_read_only_toolset


def build_fake_jboss_mcp_client() -> MultiServerMCPClient:
    """Configure stdio transport to launch the installed Python module."""

    return MultiServerMCPClient(
        {
            "fake_jboss": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "jboss_agent.mcp_server.fake_jboss_server"],
            }
        }
    )


async def load_fake_jboss_read_tools() -> tuple[MultiServerMCPClient, list[Any]]:
    """Discover MCP tools and return them as LangChain-compatible tools."""

    client = build_fake_jboss_mcp_client()
    tools = await client.get_tools()
    validate_read_only_toolset(tools)
    return client, list(tools)
