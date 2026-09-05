"""STEP 5 Fake JBoss MCP Server exposing read-only capabilities over stdio.

The project intentionally pins MCP Python SDK 1.x while
``langchain-mcp-adapters==0.3.2`` requires ``mcp<2``. The server uses the 1.x
``FastMCP`` API and can be migrated to MCP SDK 2 once the adapter supports it.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from jboss_agent.config import get_settings
from jboss_agent.jboss.fake_operations import FakeJBossOperations


mcp = FastMCP("Fake JBoss Read API")


def _operations() -> FakeJBossOperations:
    settings = get_settings()
    return FakeJBossOperations(
        settings.fake_jboss_data_dir,
        server_id=settings.server_id,
    )


@mcp.tool()
def read_server_log(server_id: str, cursor: int) -> dict[str, object]:
    """Read JBoss server.log lines added after the supplied byte cursor.

    This is read-only. Return ``to_cursor`` and use it as the next cursor rather
    than repeatedly sending the full log to an LLM.
    """

    return _operations().read_server_log(server_id, cursor)


@mcp.tool()
def get_server_health(server_id: str) -> dict[str, object]:
    """Return read-only high-level health metrics for one JBoss server."""

    return _operations().get_server_health(server_id)


@mcp.tool()
def get_thread_pool_status(server_id: str) -> dict[str, object]:
    """Return read-only worker/thread-pool saturation metrics."""

    return _operations().get_thread_pool_status(server_id)


@mcp.tool()
def get_datasource_status(server_id: str) -> dict[str, object]:
    """Return read-only datasource connection-pool metrics."""

    return _operations().get_datasource_status(server_id)


@mcp.tool()
def get_deployment_status(server_id: str) -> dict[str, object]:
    """Return read-only deployment state for the fake application."""

    return _operations().get_deployment_status(server_id)


@mcp.tool()
def get_recent_config_changes(server_id: str) -> dict[str, object]:
    """Return recent JBoss configuration changes without modifying anything."""

    return _operations().get_recent_config_changes(server_id)


def main() -> None:
    """Run as a local MCP subprocess for ``MultiServerMCPClient``."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
