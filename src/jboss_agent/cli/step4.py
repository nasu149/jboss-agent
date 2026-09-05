"""CLI runner for STEP 4 local Teams Tool calling."""

from __future__ import annotations

import json
import uuid

from jboss_agent.config import get_settings
from jboss_agent.graph.teams_tool_graph import build_step4_graph


def main() -> None:
    settings = get_settings()
    incident_id = f"inc-{uuid.uuid4().hex[:8]}"
    graph = build_step4_graph(settings=settings)
    result = graph.invoke(
        {
            "server_id": settings.server_id,
            "incident_id": incident_id,
            "incident_detected": True,
            "severity": "HIGH",
            "category": "THREAD_POOL",
            "confidence": 0.91,
            "summary": "Worker thread exhaustion is suspected from the observed log evidence.",
            "teams_notified": False,
        }
    )

    print("STEP 4: Gemini -> tools_condition -> ToolNode(send_teams_alert) -> Gemini")
    print(f"TEAMS_DRY_RUN={settings.teams_dry_run}")
    print(
        json.dumps(
            {
                "incident_id": incident_id,
                "teams_notified": result.get("teams_notified"),
                "teams_tool_status": result.get("teams_tool_status"),
                "teams_tool_result": result.get("teams_tool_result"),
                "node_trace": result.get("node_trace"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
