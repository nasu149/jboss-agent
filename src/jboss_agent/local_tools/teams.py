"""STEP 4 local Teams notification Tool.

This tool intentionally stays local Python instead of MCP. It represents an
application-side integration, while STEP 5 exposes *JBoss capabilities* through
MCP. Keeping both in one project makes the boundary concrete.
"""

from __future__ import annotations

import json
import logging
from threading import Lock
from typing import Literal

import httpx
from langchain.tools import tool
from pydantic import BaseModel, Field

from jboss_agent.config import get_settings


logger = logging.getLogger(__name__)

Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class TeamsAlertInput(BaseModel):
    """Validated schema visible to the LLM when it considers the local Tool."""

    server_id: str = Field(min_length=1, description="JBoss server identifier")
    incident_id: str = Field(min_length=1, description="Stable incident identifier")
    severity: Severity = Field(description="Incident severity")
    category: str = Field(min_length=1, description="Incident category")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence 0.0-1.0")
    summary: str = Field(min_length=1, description="Short incident summary")


_delivery_lock = Lock()
_delivered_incidents: set[str] = set()


def _format_message(alert: TeamsAlertInput) -> str:
    return (
        "[JBoss Incident Detected]\n"
        f"Server: {alert.server_id}\n"
        f"Severity: {alert.severity}\n"
        f"Category: {alert.category}\n"
        f"Confidence: {alert.confidence:.0%}\n"
        f"Summary: {alert.summary}\n"
        f"Incident ID: {alert.incident_id}"
    )


def _post_webhook(url: str, payload: dict[str, object]) -> None:
    """HTTP side effect isolated behind a tiny function for unit testing."""

    with httpx.Client(timeout=10.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()


@tool(args_schema=TeamsAlertInput)
def send_teams_alert(
    server_id: str,
    incident_id: str,
    severity: Severity,
    category: str,
    confidence: float,
    summary: str,
) -> str:
    """Send one Teams alert for a detected JBoss incident.

    Use this Tool only for user-visible incident notification. It does not read
    or modify JBoss. Duplicate calls for the same incident ID are idempotent.
    In ``TEAMS_DRY_RUN=true`` mode it logs the exact payload without network I/O.
    """

    alert = TeamsAlertInput(
        server_id=server_id,
        incident_id=incident_id,
        severity=severity,
        category=category,
        confidence=confidence,
        summary=summary,
    )
    settings = get_settings()

    with _delivery_lock:
        if incident_id in _delivered_incidents:
            result = {
                "success": True,
                "status": "duplicate_skipped",
                "incident_id": incident_id,
            }
            logger.info("Teams duplicate skipped incident_id=%s", incident_id)
            return json.dumps(result, ensure_ascii=False)

    payload: dict[str, object] = {"text": _format_message(alert)}

    if settings.teams_dry_run:
        logger.info("TEAMS_DRY_RUN payload=%s", json.dumps(payload, ensure_ascii=False))
        status = "dry_run"
    else:
        if not settings.teams_webhook_url:
            result = {
                "success": False,
                "status": "missing_webhook_url",
                "incident_id": incident_id,
            }
            logger.error("TEAMS_WEBHOOK_URL is required when TEAMS_DRY_RUN=false")
            return json.dumps(result, ensure_ascii=False)
        _post_webhook(settings.teams_webhook_url, payload)
        status = "sent"

    with _delivery_lock:
        _delivered_incidents.add(incident_id)

    result = {
        "success": True,
        "status": status,
        "incident_id": incident_id,
        "payload": payload,
    }
    return json.dumps(result, ensure_ascii=False)


def reset_delivery_registry_for_tests() -> None:
    """Clear process-local idempotency memory. Test helper only."""

    with _delivery_lock:
        _delivered_incidents.clear()
