"""STEP 4 deterministic guard before the LLM/ToolNode flow."""

from __future__ import annotations

from typing import Literal

from jboss_agent.graph.state import TeamsNotificationState


NotificationRoute = Literal["prepare_teams_request", "skip_notification"]


def route_notification_guard(state: TeamsNotificationState) -> NotificationRoute:
    if not state.get("incident_detected", False):
        return "skip_notification"
    if state.get("teams_notified", False):
        return "skip_notification"
    return "prepare_teams_request"
