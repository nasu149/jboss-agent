from dataclasses import dataclass

import pytest

from jboss_agent.mcp_client.tool_registry import (
    READ_ONLY_JBOSS_TOOL_NAMES,
    validate_read_only_toolset,
)


@dataclass
class FakeTool:
    name: str


def test_read_only_registry_accepts_expected_tools() -> None:
    validate_read_only_toolset([FakeTool(name) for name in READ_ONLY_JBOSS_TOOL_NAMES])


def test_read_only_registry_blocks_write_tool() -> None:
    tools = [FakeTool(name) for name in READ_ONLY_JBOSS_TOOL_NAMES]
    tools.append(FakeTool("reload_server"))

    with pytest.raises(RuntimeError, match="Unsafe tools"):
        validate_read_only_toolset(tools)


def test_full_registry_contains_only_explicit_capabilities() -> None:
    from jboss_agent.mcp_client.tool_registry import (
        READ_ONLY_JBOSS_TOOL_NAMES,
        WRITE_JBOSS_TOOL_NAMES,
        validate_server_toolset,
    )

    tools = [FakeTool(name) for name in (READ_ONLY_JBOSS_TOOL_NAMES | WRITE_JBOSS_TOOL_NAMES)]
    validate_server_toolset(tools)
