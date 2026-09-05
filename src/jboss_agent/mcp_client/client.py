"""LangChain adapters for the local Fake JBoss MCP Server."""

from __future__ import annotations

import sys
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from jboss_agent.mcp_client.tool_registry import (
    READ_ONLY_JBOSS_TOOL_NAMES,
    WRITE_JBOSS_TOOL_NAMES,
    validate_read_only_toolset,
    validate_server_toolset,
    validate_write_toolset,
)


def build_fake_jboss_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(
        {
            "fake_jboss": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "jboss_agent.mcp_server.fake_jboss_server"],
            }
        }
    )


async def _load_all_tools() -> tuple[MultiServerMCPClient, list[Any]]:
    client = build_fake_jboss_mcp_client()
    tools = list(await client.get_tools())
    validate_server_toolset(tools)
    return client, tools


async def load_fake_jboss_read_tools() -> tuple[MultiServerMCPClient, list[Any]]:
    """Return exactly the read-only subset, even though STEP 8 server has writes."""
    client, all_tools = await _load_all_tools()
    tools = [tool for tool in all_tools if tool.name in READ_ONLY_JBOSS_TOOL_NAMES]
    validate_read_only_toolset(tools)
    return client, tools


async def load_fake_jboss_write_tools() -> tuple[MultiServerMCPClient, list[Any]]:
    """Return exactly the post-approval write subset."""
    client, all_tools = await _load_all_tools()
    tools = [tool for tool in all_tools if tool.name in WRITE_JBOSS_TOOL_NAMES]
    validate_write_toolset(tools)
    return client, tools


async def load_fake_jboss_read_write_tools() -> tuple[MultiServerMCPClient, list[Any], list[Any]]:
    client, all_tools = await _load_all_tools()
    read_tools = [tool for tool in all_tools if tool.name in READ_ONLY_JBOSS_TOOL_NAMES]
    write_tools = [tool for tool in all_tools if tool.name in WRITE_JBOSS_TOOL_NAMES]
    validate_read_only_toolset(read_tools)
    validate_write_toolset(write_tools)
    return client, read_tools, write_tools
