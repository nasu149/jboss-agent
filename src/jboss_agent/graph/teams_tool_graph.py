"""STEP 4: local @tool + Gemini tool calling + tools_condition + ToolNode."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from jboss_agent.config import Settings, get_settings
from jboss_agent.graph.nodes.skip_notification import skip_notification
from jboss_agent.graph.nodes.teams_notification import (
    MessageModel,
    make_call_teams_tool_node,
    make_finalize_teams_node,
    notification_guard,
    prepare_teams_request,
)
from jboss_agent.graph.routes.teams_routes import route_notification_guard
from jboss_agent.graph.state import TeamsNotificationState
from jboss_agent.llm.gemini import build_gemini_client
from jboss_agent.local_tools.teams import send_teams_alert


def build_step4_graph(
    *,
    settings: Settings | None = None,
    tool_calling_model: MessageModel | None = None,
    final_model: MessageModel | None = None,
):
    """Compile the STEP 4 Tool calling graph.

    The first Gemini binding forces one tool call because the purpose of this
    learning step is to observe the ToolNode mechanics, not to debate whether a
    pre-validated incident should be notified. The second Gemini call receives
    the ToolMessage without tools bound, completing the classic
    LLM -> ToolNode -> LLM round trip once.
    """

    resolved_settings = settings or get_settings()
    base_model = None

    if tool_calling_model is None:
        base_model = build_gemini_client(resolved_settings)
        resolved_tool_model: MessageModel = base_model.bind_tools(
            [send_teams_alert],
            tool_choice="any",
        )
    else:
        resolved_tool_model = tool_calling_model

    if final_model is None:
        if base_model is None:
            base_model = build_gemini_client(resolved_settings)
        resolved_final_model: MessageModel = base_model
    else:
        resolved_final_model = final_model

    builder = StateGraph(TeamsNotificationState)
    builder.add_node("notification_guard", notification_guard)
    builder.add_node("skip_notification", skip_notification)
    builder.add_node("prepare_teams_request", prepare_teams_request)
    builder.add_node("call_teams_tool", make_call_teams_tool_node(resolved_tool_model))
    builder.add_node("tools", ToolNode([send_teams_alert]))
    builder.add_node("finalize_teams", make_finalize_teams_node(resolved_final_model))

    builder.add_edge(START, "notification_guard")
    builder.add_conditional_edges("notification_guard", route_notification_guard)
    builder.add_edge("skip_notification", END)
    builder.add_edge("prepare_teams_request", "call_teams_tool")
    builder.add_conditional_edges("call_teams_tool", tools_condition)
    builder.add_edge("tools", "finalize_teams")
    builder.add_edge("finalize_teams", END)

    return builder.compile()
