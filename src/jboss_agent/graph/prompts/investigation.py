"""Prompts for the STEP 6 read-only investigation agent."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from jboss_agent.graph.state import IncidentState


INVESTIGATION_SYSTEM_PROMPT = """You are a JBoss incident investigator.
You have READ-ONLY JBoss tools only. Select only the tools needed to test the
current hypothesis. Never assume the initial category is correct.

Rules:
- Use tool evidence before concluding.
- Prefer 1-3 relevant calls over querying everything blindly.
- Do not ask for or invent write operations.
- Do not claim a configuration value unless a tool returned it.
- When you have enough evidence, respond with a concise evidence summary and make
  no further tool calls. A separate structured diagnosis step will run next.
"""


def initial_investigation_messages(state: IncidentState) -> list[object]:
    logs = "\n".join(state.get("initial_log_lines", [])) or "(no initial logs supplied)"
    return [
        SystemMessage(content=INVESTIGATION_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Incident ID: {state['incident_id']}\n"
                f"Server: {state['server_id']}\n"
                f"Initial category hint: {state.get('category', 'UNKNOWN')}\n"
                f"Severity: {state.get('severity', 'UNKNOWN')}\n"
                f"Initial log evidence:\n{logs}\n\n"
                "Investigate the cause using the available read-only tools."
            )
        ),
    ]
