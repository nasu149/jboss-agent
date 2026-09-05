"""Gemini bindings used by STEP 6-9 incident response graphs."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from jboss_agent.config import Settings
from jboss_agent.domain.models import IncidentDiagnosis
from jboss_agent.llm.gemini import build_gemini_client


def build_investigation_model(settings: Settings, read_tools: Sequence[Any]):
    """Bind only read-only MCP tools for autonomous investigation."""
    model = build_gemini_client(settings)
    return model.bind_tools(list(read_tools))


def build_diagnosis_model(settings: Settings):
    """Bind Gemini to a structured diagnosis schema after tool gathering."""
    model = build_gemini_client(settings)
    return model.with_structured_output(
        schema=IncidentDiagnosis.model_json_schema(),
        method="json_schema",
    )
