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


def validate_read_only_toolset(tools: Iterable[NamedTool]) -> None:
    """Fail fast if STEP 5 accidentally exposes write/arbitrary execution tools."""

    names = {tool.name for tool in tools}
    missing = READ_ONLY_JBOSS_TOOL_NAMES - names
    unsafe = names & (WRITE_JBOSS_TOOL_NAMES | FORBIDDEN_GENERIC_TOOL_NAMES)
    if missing:
        raise RuntimeError(f"Fake JBoss MCP server is missing read tools: {sorted(missing)}")
    if unsafe:
        raise RuntimeError(f"Unsafe tools exposed during read-only STEP 5: {sorted(unsafe)}")
