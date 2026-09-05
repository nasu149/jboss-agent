"""STEP 2 node that delegates ambiguous log interpretation to Gemini."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from jboss_agent.domain.models import LogClassification
from jboss_agent.graph.prompts.log_analysis import build_log_analysis_prompt
from jboss_agent.graph.state import MonitoringState
from jboss_agent.llm.log_classifier import LogClassifier


def make_analyze_logs_node(classifier: LogClassifier):
    """Create a testable LangGraph node around an injected structured classifier."""

    def analyze_logs(state: MonitoringState) -> dict[str, object]:
        log_text = state.get("log_text", "")
        if not log_text.strip():
            raise ValueError("log_text is empty; collect_fake_log must run first")

        raw_result = classifier.invoke(build_log_analysis_prompt(log_text))
        if isinstance(raw_result, LogClassification):
            classification = raw_result
        elif isinstance(raw_result, Mapping):
            classification = LogClassification.model_validate(dict(raw_result))
        else:
            raise TypeError(
                "Structured classifier returned an unsupported type: "
                f"{type(raw_result).__name__}"
            )

        trace = [*state.get("node_trace", []), "analyze_logs"]
        return {
            "incident_detected": classification.incident_detected,
            "category": classification.category,
            "confidence": classification.confidence,
            "summary": classification.summary,
            "evidence": classification.evidence,
            "node_trace": trace,
        }

    return analyze_logs
