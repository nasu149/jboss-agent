"""STEP 4 nodes around the local Teams Tool calling flow."""

from __future__ import annotations

import json
from typing import Protocol

from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage

from jboss_agent.graph.state import TeamsNotificationState


class MessageModel(Protocol):
    def invoke(self, input: object) -> BaseMessage:  # noqa: A002 - LangChain naming
        ...


def notification_guard(state: TeamsNotificationState) -> dict[str, object]:
    """Python guard: only an unnotified incident is eligible for the Tool flow."""

    trace = [*state.get("node_trace", []), "notification_guard"]
    return {"node_trace": trace}


def prepare_teams_request(state: TeamsNotificationState) -> dict[str, object]:
    """Put an explicit notification request into Messages State."""

    message = HumanMessage(
        content=(
            "A JBoss incident has already been detected and validated by the monitoring graph. "
            "Call send_teams_alert exactly once with these fields. Do not invent values.\n"
            f"server_id={state['server_id']}\n"
            f"incident_id={state['incident_id']}\n"
            f"severity={state['severity']}\n"
            f"category={state['category']}\n"
            f"confidence={state['confidence']}\n"
            f"summary={state['summary']}"
        )
    )
    trace = [*state.get("node_trace", []), "prepare_teams_request"]
    return {"messages": [message], "node_trace": trace}


def make_call_teams_tool_node(tool_calling_model: MessageModel):
    """LLM node whose output should contain a structured tool call."""

    def call_teams_tool(state: TeamsNotificationState) -> dict[str, object]:
        response = tool_calling_model.invoke(state.get("messages", []))
        trace = [*state.get("node_trace", []), "call_teams_tool"]
        return {"messages": [response], "node_trace": trace}

    return call_teams_tool


def make_finalize_teams_node(final_model: MessageModel):
    """Read ToolMessage, update ordinary State, then let the LLM summarize once."""

    def finalize_teams(state: TeamsNotificationState) -> dict[str, object]:
        messages = state.get("messages", [])
        tool_message = next(
            (message for message in reversed(messages) if isinstance(message, ToolMessage)),
            None,
        )
        if tool_message is None:
            raise ValueError("ToolNode produced no ToolMessage")

        try:
            tool_result = json.loads(str(tool_message.content))
        except json.JSONDecodeError as exc:
            raise ValueError("send_teams_alert returned invalid JSON") from exc

        success = bool(tool_result.get("success"))
        status = str(tool_result.get("status", "unknown"))
        response = final_model.invoke(
            [
                *messages,
                HumanMessage(
                    content=(
                        "Summarize the Teams notification Tool result in one short sentence. "
                        "Do not call any tool."
                    )
                ),
            ]
        )
        trace = [*state.get("node_trace", []), "finalize_teams"]
        return {
            "messages": [response],
            "teams_notified": success,
            "teams_tool_status": status,
            "teams_tool_result": tool_result,
            "node_trace": trace,
        }

    return finalize_teams
