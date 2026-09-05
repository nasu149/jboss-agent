"""Fake JBoss MCP Server exposing explicit read and write capabilities over stdio.

STEP 5 clients deliberately filter this server down to read-only tools. STEP 8
adds the write capabilities, but investigation agents still receive only the
read-only subset.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from jboss_agent.config import get_settings
from jboss_agent.jboss.fake_operations import FakeJBossOperations


mcp = FastMCP("Fake JBoss Capability API")


def _operations() -> FakeJBossOperations:
    settings = get_settings()
    return FakeJBossOperations(settings.fake_jboss_data_dir, server_id=settings.server_id)


@mcp.tool()
def read_server_log(server_id: str, cursor: int) -> dict[str, object]:
    """Read JBoss server.log lines added after a byte cursor. Read-only."""
    return _operations().read_server_log(server_id, cursor)


@mcp.tool()
def get_server_health(server_id: str) -> dict[str, object]:
    """Return read-only high-level server health metrics."""
    return _operations().get_server_health(server_id)


@mcp.tool()
def get_thread_pool_status(server_id: str) -> dict[str, object]:
    """Return read-only worker thread-pool saturation metrics."""
    return _operations().get_thread_pool_status(server_id)


@mcp.tool()
def get_datasource_status(server_id: str) -> dict[str, object]:
    """Return read-only datasource connection-pool metrics."""
    return _operations().get_datasource_status(server_id)


@mcp.tool()
def get_deployment_status(server_id: str) -> dict[str, object]:
    """Return read-only deployment state."""
    return _operations().get_deployment_status(server_id)


@mcp.tool()
def get_recent_config_changes(server_id: str) -> dict[str, object]:
    """Return recent configuration changes without modifying JBoss."""
    return _operations().get_recent_config_changes(server_id)


@mcp.tool()
def set_thread_pool_max_threads(server_id: str, value: int) -> dict[str, object]:
    """Set worker max_threads to a validated value from 1 through 200.

    This is a write capability. The incident investigation LLM must never receive
    this tool. LangGraph may execute it only after risk validation and approval.
    """
    return _operations().set_thread_pool_max_threads(server_id, value)


@mcp.tool()
def set_datasource_max_pool_size(server_id: str, value: int) -> dict[str, object]:
    """Set datasource max_pool_size to a validated value from 1 through 200.

    This write capability is intended only for post-approval execution.
    """
    return _operations().set_datasource_max_pool_size(server_id, value)


@mcp.tool()
def restart_deployment(server_id: str, deployment_name: str) -> dict[str, object]:
    """Restart one named deployment after explicit human approval."""
    return _operations().restart_deployment(server_id, deployment_name)


@mcp.tool()
def reload_server(server_id: str) -> dict[str, object]:
    """Reload the fake JBoss server after explicit human approval."""
    return _operations().reload_server(server_id)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
