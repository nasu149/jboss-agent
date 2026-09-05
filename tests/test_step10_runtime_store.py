from __future__ import annotations

from jboss_agent.runtime.store import RuntimeStore


def test_runtime_store_tracks_monitoring_and_pending_incident(tmp_path) -> None:
    store = RuntimeStore(tmp_path / "runtime.sqlite")
    store.begin_scan("jboss-test", next_scan_at="2026-09-05T10:03:00+00:00")
    store.complete_scan(
        "jboss-test",
        previous_cursor=10,
        current_cursor=42,
        incident_id="inc-10",
    )
    status = store.get_monitoring_status("jboss-test")
    assert status.current_cursor == 42
    assert status.last_incident_id == "inc-10"

    store.upsert_incident(
        incident_id="inc-10",
        thread_id="incident:inc-10",
        server_id="jboss-test",
        category="THREAD_POOL",
        severity="HIGH",
        confidence=0.9,
        summary="thread issue",
        status="PENDING_APPROVAL",
        pending_approval={"action": "SET_THREAD_POOL_MAX_THREADS", "proposed_value": 80},
    )
    pending = store.list_pending_approvals()
    assert len(pending) == 1
    assert pending[0].pending_approval["proposed_value"] == 80


def test_runtime_activity_is_durable(tmp_path) -> None:
    path = tmp_path / "runtime.sqlite"
    RuntimeStore(path).add_activity("jboss-test", "monitoring", "scan started")
    rows = RuntimeStore(path).list_activity("jboss-test")
    assert rows[0]["message"] == "scan started"
