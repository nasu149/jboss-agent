"""Pure-Python evaluation metrics for STEP 12."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from jboss_agent.simulator.scenarios import GroundTruthScenario, is_incident_scenario


@dataclass(frozen=True)
class EvaluationTrial:
    trial: int
    ground_truth: GroundTruthScenario
    incident_expected: bool
    incident_detected: bool
    diagnosis: str | None
    diagnosis_correct: bool
    false_positive: bool
    false_negative: bool
    recovered: bool
    human_rejected: bool
    investigation_tool_calls: int
    incident_id: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_diagnosis(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "THREAD_POOL": "THREAD_POOL_CONFIGURATION",
        "THREAD_POOL_EXHAUSTION": "THREAD_POOL_CONFIGURATION",
        "THREAD_POOL_CONFIGURATION": "THREAD_POOL_CONFIGURATION",
        "DATASOURCE": "DATASOURCE_POOL_EXHAUSTION",
        "DATASOURCE_POOL": "DATASOURCE_POOL_EXHAUSTION",
        "DATASOURCE_POOL_EXHAUSTION": "DATASOURCE_POOL_EXHAUSTION",
        "DEPLOYMENT": "DEPLOYMENT_FAILURE",
        "DEPLOYMENT_FAILURE": "DEPLOYMENT_FAILURE",
        "NORMAL": "NORMAL_ACTIVITY",
        "NORMAL_ACTIVITY": "NORMAL_ACTIVITY",
    }
    return aliases.get(text, text)


def build_trial(
    *,
    trial: int,
    ground_truth: GroundTruthScenario,
    incident_detected: bool,
    diagnosis: str | None,
    recovered: bool,
    human_rejected: bool,
    investigation_tool_calls: int,
    incident_id: str | None,
) -> EvaluationTrial:
    expected = is_incident_scenario(ground_truth)
    normalized = normalize_diagnosis(diagnosis)
    diagnosis_correct = (not expected and not incident_detected) or (
        expected and normalized == ground_truth
    )
    return EvaluationTrial(
        trial=trial,
        ground_truth=ground_truth,
        incident_expected=expected,
        incident_detected=incident_detected,
        diagnosis=normalized,
        diagnosis_correct=diagnosis_correct,
        false_positive=not expected and incident_detected,
        false_negative=expected and not incident_detected,
        recovered=recovered,
        human_rejected=human_rejected,
        investigation_tool_calls=investigation_tool_calls,
        incident_id=incident_id,
    )


def summarize_trials(trials: Iterable[EvaluationTrial]) -> dict[str, Any]:
    rows = list(trials)
    total = len(rows)
    if total == 0:
        raise ValueError("at least one evaluation trial is required")

    correct_detection = sum(row.incident_expected == row.incident_detected for row in rows)
    fault_rows = [row for row in rows if row.incident_expected]
    diagnosis_correct = sum(row.diagnosis_correct for row in fault_rows)
    recovered = sum(row.recovered for row in fault_rows)
    tool_calls = sum(row.investigation_tool_calls for row in rows)

    return {
        "runs": total,
        "incident_detection_accuracy": correct_detection / total,
        "false_positive_count": sum(row.false_positive for row in rows),
        "false_negative_count": sum(row.false_negative for row in rows),
        "diagnosis_accuracy": diagnosis_correct / len(fault_rows) if fault_rows else 1.0,
        "recovery_success_rate": recovered / len(fault_rows) if fault_rows else 1.0,
        "human_rejection_count": sum(row.human_rejected for row in rows),
        "average_investigation_tool_calls": tool_calls / total,
    }
