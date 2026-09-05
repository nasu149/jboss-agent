"""Structured diagnosis after STEP 6 read-only evidence gathering."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from jboss_agent.domain.models import IncidentDiagnosis
from jboss_agent.graph.prompts.diagnosis import build_diagnosis_prompt
from jboss_agent.graph.state import IncidentState


class StructuredDiagnosisModel(Protocol):
    def invoke(self, input: str) -> object:  # noqa: A002
        ...


def make_diagnose_node(model: StructuredDiagnosisModel):
    def diagnose(state: IncidentState) -> dict[str, object]:
        raw = model.invoke(build_diagnosis_prompt(state))
        if isinstance(raw, IncidentDiagnosis):
            diagnosis = raw
        elif isinstance(raw, Mapping):
            diagnosis = IncidentDiagnosis.model_validate(dict(raw))
        else:
            raise TypeError(f"diagnosis model returned unsupported type: {type(raw).__name__}")

        trace = [*state.get("node_trace", []), "diagnose"]
        return {
            "diagnosis": diagnosis.model_dump(),
            "proposed_action": diagnosis.recommended_action.model_dump(),
            "node_trace": trace,
        }

    return diagnose
