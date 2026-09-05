"""Gemini structured-output classifier used by STEP 2."""

from __future__ import annotations

from typing import Protocol

from jboss_agent.config import Settings
from jboss_agent.domain.models import LogClassification
from jboss_agent.llm.gemini import build_gemini_client


class LogClassifier(Protocol):
    """Minimal interface needed by the graph node and its tests."""

    def invoke(self, input: str) -> object:  # noqa: A002 - LangChain API naming
        ...


def build_log_classifier(settings: Settings) -> LogClassifier:
    """Bind Gemini to a native JSON schema for deterministic response shape."""

    model = build_gemini_client(settings)
    return model.with_structured_output(
        schema=LogClassification.model_json_schema(),
        method="json_schema",
    )
