"""Expected MCP capability names and safety checks."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol


READ_ONLY_JBOSS_TOOL_NAMES = frozenset(
    {
        "read_server_log",
        "get_server_health",
        "get_thread_pool_status",
        "get_datasource_status",
        "get_deployment_status",
        "get_recent_config_changes",
    }
)

WRITE_JBOSS_TOOL_NAMES = frozenset(
    {
        "set_thread_pool_max_threads",
        "set_datasource_max_pool_size",
        "restart_deployment",
        "reload_server",
    }
)

FORBIDDEN_GENERIC_TOOL_NAMES = frozenset({"execute_jboss_cli", "execute_shell"})


class NamedTool(Protocol):
    name: str


def _names(tools: Iterable[NamedTool]) -> set[str]:
    return {tool.name for tool in tools}


def validate_server_toolset(tools: Iterable[NamedTool]) -> None:
    names = _names(tools)
    expected = READ_ONLY_JBOSS_TOOL_NAMES | WRITE_JBOSS_TOOL_NAMES
    missing = expected - names
    forbidden = names & FORBIDDEN_GENERIC_TOOL_NAMES
    unexpected = names - expected
    if missing:
        raise RuntimeError(f"Fake JBoss MCP server is missing tools: {sorted(missing)}")
    if forbidden:
        raise RuntimeError(f"Forbidden generic tools are exposed: {sorted(forbidden)}")
    if unexpected:
        raise RuntimeError(f"Unexpected MCP tools are exposed: {sorted(unexpected)}")


def validate_read_only_toolset(tools: Iterable[NamedTool]) -> None:
    names = _names(tools)
    missing = READ_ONLY_JBOSS_TOOL_NAMES - names
    unsafe = names & (WRITE_JBOSS_TOOL_NAMES | FORBIDDEN_GENERIC_TOOL_NAMES)
    if missing:
        raise RuntimeError(f"Fake JBoss MCP server is missing read tools: {sorted(missing)}")
    if unsafe:
        raise RuntimeError(f"Unsafe tools exposed to investigation: {sorted(unsafe)}")


def validate_write_toolset(tools: Iterable[NamedTool]) -> None:
    names = _names(tools)
    missing = WRITE_JBOSS_TOOL_NAMES - names
    forbidden = names & FORBIDDEN_GENERIC_TOOL_NAMES
    unexpected_reads = names & READ_ONLY_JBOSS_TOOL_NAMES
    if missing:
        raise RuntimeError(f"Fake JBoss MCP server is missing write tools: {sorted(missing)}")
    if forbidden:
        raise RuntimeError(f"Forbidden generic tools are exposed: {sorted(forbidden)}")
    if unexpected_reads:
        raise RuntimeError(f"Write-only execution set unexpectedly includes reads: {sorted(unexpected_reads)}")
