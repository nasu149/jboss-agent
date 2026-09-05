from __future__ import annotations

from jboss_agent.evaluation.metrics import build_trial, normalize_diagnosis, summarize_trials


def test_diagnosis_aliases_are_normalized() -> None:
    assert normalize_diagnosis("thread pool") == "THREAD_POOL_CONFIGURATION"
    assert normalize_diagnosis("DEPLOYMENT_FAILURE") == "DEPLOYMENT_FAILURE"


def test_step12_summary_counts_false_positive_and_tool_calls() -> None:
    rows = [
        build_trial(
            trial=1,
            ground_truth="THREAD_POOL_CONFIGURATION",
            incident_detected=True,
            diagnosis="THREAD_POOL_CONFIGURATION",
            recovered=True,
            human_rejected=False,
            investigation_tool_calls=2,
            incident_id="inc-1",
        ),
        build_trial(
            trial=2,
            ground_truth="NORMAL_ACTIVITY",
            incident_detected=True,
            diagnosis="UNKNOWN",
            recovered=False,
            human_rejected=False,
            investigation_tool_calls=1,
            incident_id="inc-2",
        ),
    ]
    summary = summarize_trials(rows)
    assert summary["incident_detection_accuracy"] == 0.5
    assert summary["false_positive_count"] == 1
    assert summary["diagnosis_accuracy"] == 1.0
    assert summary["recovery_success_rate"] == 1.0
    assert summary["average_investigation_tool_calls"] == 1.5
