"""Fault scenarios used by STEP 11 UI and STEP 12 evaluation.

Scenario labels are ground truth. They must never be placed into LangGraph Agent
State or LLM prompts.
"""

from __future__ import annotations

from typing import Literal


GroundTruthScenario = Literal[
    "THREAD_POOL_CONFIGURATION",
    "DATASOURCE_POOL_EXHAUSTION",
    "DEPLOYMENT_FAILURE",
    "NORMAL_ACTIVITY",
]

SCENARIOS: tuple[GroundTruthScenario, ...] = (
    "THREAD_POOL_CONFIGURATION",
    "DATASOURCE_POOL_EXHAUSTION",
    "DEPLOYMENT_FAILURE",
    "NORMAL_ACTIVITY",
)

FAULT_SCENARIOS = frozenset(SCENARIOS[:-1])


def is_incident_scenario(scenario: GroundTruthScenario) -> bool:
    return scenario in FAULT_SCENARIOS
