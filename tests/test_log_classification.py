import pytest
from pydantic import ValidationError

from jboss_agent.domain.models import LogClassification


def test_log_classification_accepts_expected_schema() -> None:
    result = LogClassification.model_validate(
        {
            "incident_detected": True,
            "category": "THREAD_POOL",
            "confidence": 0.87,
            "summary": "worker exhaustion suspected",
            "evidence": ["task rejected"],
        }
    )

    assert result.category == "THREAD_POOL"
    assert result.confidence == 0.87


def test_log_classification_rejects_unknown_category_name() -> None:
    with pytest.raises(ValidationError):
        LogClassification.model_validate(
            {
                "incident_detected": True,
                "category": "CPU",
                "confidence": 0.8,
                "summary": "not in the allowed taxonomy",
                "evidence": [],
            }
        )
