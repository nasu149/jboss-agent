from __future__ import annotations

from dataclasses import dataclass

import pytest

from jboss_agent.domain.models import IncidentCategory
from jboss_agent.graph.monitoring_graph import build_step2_graph


@dataclass
class FakeClassifier:
    category: IncidentCategory

    def invoke(self, input: str) -> object:  # noqa: A002 - mirrors LangChain
        assert "LOG LINES:" in input
        return {
            "incident_detected": self.category != "NORMAL",
            "category": self.category,
            "confidence": 0.91,
            "summary": f"classified as {self.category}",
            "evidence": ["test evidence"],
        }


@pytest.mark.parametrize(
    ("category", "expected_route"),
    [
        ("NORMAL", "normal_branch"),
        ("THREAD_POOL", "thread_pool_branch"),
        ("DATASOURCE_POOL", "datasource_pool_branch"),
        ("DEPLOYMENT", "deployment_branch"),
        ("UNKNOWN", "unknown_branch"),
    ],
)
def test_step2_conditional_edge_routes_by_structured_category(
    category: IncidentCategory,
    expected_route: str,
) -> None:
    graph = build_step2_graph(classifier=FakeClassifier(category))

    result = graph.invoke({"input_log_lines": ["2026-09-05 INFO raw log only"]})

    assert result["category"] == category
    assert result["route_taken"] == expected_route
    assert result["node_trace"] == [
        "collect_fake_log",
        "analyze_logs",
        expected_route,
    ]
