"""Prompt construction for STEP 2 log classification."""

from __future__ import annotations


_SYSTEM_GUIDANCE = """You classify JBoss EAP-like server logs for incident monitoring.
Use only the supplied log lines as evidence. Do not invent metrics, configuration values,
or a hidden scenario. Choose exactly one category:
- NORMAL: normal activity with no incident evidence
- THREAD_POOL: worker/executor/thread exhaustion or saturation
- DATASOURCE_POOL: JDBC/datasource connection pool exhaustion or acquisition timeout
- DEPLOYMENT: deployment/startup/rollback/service dependency failure
- UNKNOWN: suspicious or abnormal evidence that does not fit the categories above

Set incident_detected=false for genuinely normal activity. Keep evidence concise.
"""


def build_log_analysis_prompt(log_text: str) -> str:
    """Create the input sent to the structured Gemini classifier."""

    return f"{_SYSTEM_GUIDANCE}\n\nLOG LINES:\n{log_text}"
