from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jboss_agent.graph.cursor_monitoring_graph import build_step3_graph
from jboss_agent.jboss.fake_operations import FakeJBossOperations


@dataclass
class CountingClassifier:
    calls: int = 0

    def invoke(self, input: str) -> object:  # noqa: A002
        self.calls += 1
        category = "THREAD_POOL" if "worker" in input else "NORMAL"
        return {
            "incident_detected": category != "NORMAL",
            "category": category,
            "confidence": 0.9,
            "summary": "test classification",
            "evidence": ["worker" if category == "THREAD_POOL" else "info"],
        }


def test_step3_cursor_skips_llm_when_no_new_logs(tmp_path: Path) -> None:
    fake = FakeJBossOperations(tmp_path / "fake", server_id="jboss-test")
    fake.reset(include_boot_logs=False)
    fake.append_log_lines(["2026 INFO request completed"])
    classifier = CountingClassifier()
    graph = build_step3_graph(reader=fake, classifier=classifier)

    first = graph.invoke({"server_id": "jboss-test", "previous_log_cursor": 0})
    assert classifier.calls == 1
    assert first["route_taken"] == "normal_branch"

    cursor = int(first["current_log_cursor"])
    second = graph.invoke({"server_id": "jboss-test", "previous_log_cursor": cursor})
    assert classifier.calls == 1
    assert second["route_taken"] == "no_new_logs"
    assert second["node_trace"] == ["collect_logs", "no_new_logs"]

    fake.append_log_lines(["2026 ERROR no worker thread available"])
    third = graph.invoke({"server_id": "jboss-test", "previous_log_cursor": cursor})
    assert classifier.calls == 2
    assert third["new_log_lines"] == ["2026 ERROR no worker thread available"]
    assert third["route_taken"] == "thread_pool_branch"
