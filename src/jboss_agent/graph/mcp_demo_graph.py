"""STEP 5 graph that executes an MCP-derived LangChain Tool through ToolNode."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from jboss_agent.graph.state import MCPDemoState


def build_step5_graph(tools: Sequence[Any], *, tool_name: str = "get_server_health"):
    """Compile a deterministic MCP integration demo.

    STEP 6 lets Gemini choose among MCP read tools. STEP 5 intentionally emits
    one tool call in ordinary Python so MCP discovery/execution can be learned
    independently from agentic tool selection.
    """

    tool_names = {tool.name for tool in tools}
    if tool_name not in tool_names:
        raise ValueError(f"MCP tool not available: {tool_name}")

    def request_mcp_tool(state: MCPDemoState) -> dict[str, object]:
        server_id = state["server_id"]
        message = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": tool_name,
                    "args": {"server_id": server_id},
                    "id": "step5-mcp-read-1",
                    "type": "tool_call",
                }
            ],
        )
        return {"messages": [message], "requested_tool": tool_name}

    builder = StateGraph(MCPDemoState)
    builder.add_node("request_mcp_tool", request_mcp_tool)
    builder.add_node("tools", ToolNode(list(tools)))
    builder.add_edge(START, "request_mcp_tool")
    builder.add_edge("request_mcp_tool", "tools")
    builder.add_edge("tools", END)
    return builder.compile()
