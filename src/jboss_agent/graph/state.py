"""LangGraph State definitions for STEP 1 and STEP 2."""

from __future__ import annotations

from typing import TypedDict

from jboss_agent.domain.models import IncidentCategory


class CoreLearningState(TypedDict, total=False):
    """Minimal state used by STEP 1.

    ``input_log_lines`` is optional input. ``collect_fake_log`` converts it into
    ``log_text`` so later nodes do not care where the lines came from.
    """

    input_log_lines: list[str]
    log_text: str
    simple_check_result: str
    node_trace: list[str]


class MonitoringState(CoreLearningState, total=False):
    """STEP 2 state extended with the structured LLM classification."""

    incident_detected: bool
    category: IncidentCategory
    confidence: float
    summary: str
    evidence: list[str]
    route_taken: str
