"""STEP 6 nodes for LLM-driven read-only investigation."""

from __future__ import annotations

from typing import Protocol

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from jboss_agent.graph.prompts.investigation import initial_investigation_messages
from jboss_agent.graph.state import IncidentState


class MessageModel(Protocol):
    def invoke(self, input: object) -> BaseMessage:  # noqa: A002
        ...


def prepare_investigation(state: IncidentState) -> dict[str, object]:
    """Seed the MessagesState once with incident context; no LLM call here."""
    trace = [*state.get("node_trace", []), "prepare_investigation"]
    if state.get("messages"):
        return {"node_trace": trace}
    return {
        "messages": initial_investigation_messages(state),
        "investigation_count": state.get("investigation_count", 0),
        "evidence": state.get("evidence", []),
        "recovery_attempts": state.get("recovery_attempts", 0),
        "node_trace": trace,
    }


def make_investigator_node(model: MessageModel):
    """Ask Gemini to choose the next read-only MCP Tool or stop investigating."""

    def investigate(state: IncidentState) -> dict[str, object]:
        response = model.invoke(state["messages"])
        if not isinstance(response, AIMessage):
            raise TypeError(f"investigation model must return AIMessage, got {type(response).__name__}")
        trace = [*state.get("node_trace", []), "investigate"]
        return {
            "messages": [response],
            "investigation_count": state.get("investigation_count", 0) + 1,
            "node_trace": trace,
        }

    return investigate


def route_after_investigator(state: IncidentState) -> str:
    """Tool calls go to ToolNode; a plain answer means evidence gathering is done."""
    messages = state.get("messages", [])
    if not messages:
        return "diagnose"
    last = messages[-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "read_tools"
    return "diagnose"


def record_tool_evidence(state: IncidentState) -> dict[str, object]:
    """Copy the most recent ToolMessages into durable, model-independent evidence."""
    recent: list[ToolMessage] = []
    for message in reversed(state.get("messages", [])):
        if isinstance(message, ToolMessage):
            recent.append(message)
            continue
        break
    recent.reverse()

    evidence = [*state.get("evidence", [])]
    for message in recent:
        evidence.append(
            {
                "tool_name": message.name or "unknown_tool",
                "tool_call_id": message.tool_call_id,
                "content": message.content,
            }
        )
    trace = [*state.get("node_trace", []), "record_tool_evidence"]
    return {"evidence": evidence, "node_trace": trace}


def make_route_after_tool_evidence(max_rounds: int):
    def route(state: IncidentState) -> str:
        if state.get("investigation_count", 0) >= max_rounds:
            return "diagnose"
        return "investigate"

    return route
