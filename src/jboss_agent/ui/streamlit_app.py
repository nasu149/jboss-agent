"""STEP 11 operational Streamlit UI.

The UI does not contain incident reasoning. It reads dashboard metadata, invokes
existing application services, injects simulator events, and resumes pending
LangGraph interrupts with ``Command(resume=...)`` through the runtime service.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import streamlit as st

from jboss_agent.config import get_settings
from jboss_agent.evaluation.metrics import normalize_diagnosis
from jboss_agent.jboss.fake_operations import FakeJBossOperations
from jboss_agent.runtime.service import OperationalAgentService
from jboss_agent.runtime.store import IncidentRecord, RuntimeStore
from jboss_agent.simulator.fault_injector import FaultInjector
from jboss_agent.simulator.ground_truth import GroundTruthEvent, GroundTruthStore
from jboss_agent.simulator.scenarios import SCENARIOS


settings = get_settings()
runtime_store = RuntimeStore(settings.runtime_db_path)
truth_store = GroundTruthStore(settings.simulator_db_path)
service = OperationalAgentService(settings, runtime_store=runtime_store, truth_store=truth_store)
fake = FakeJBossOperations(settings.fake_jboss_data_dir, server_id=settings.server_id)
fake.ensure_initialized()
injector = FaultInjector(fake, truth_store)


def run_async(coro: Any) -> Any:
    return asyncio.run(coro)


def terminal(record: IncidentRecord) -> bool:
    return record.status not in {"INVESTIGATING", "PENDING_APPROVAL"}


def render_server_snapshot() -> None:
    health = fake.get_server_health(settings.server_id)
    thread_pool = fake.get_thread_pool_status(settings.server_id)
    datasource = fake.get_datasource_status(settings.server_id)
    deployment = fake.get_deployment_status(settings.server_id)

    st.subheader("Server status")
    cols = st.columns(4)
    cols[0].metric("Server", str(health["status"]))
    cols[1].metric("Error rate", f"{float(health['request_error_rate']):.1%}")
    cols[2].metric(
        "Thread pool",
        f"{thread_pool['active_threads']}/{thread_pool['max_threads']}",
        help=f"queue={thread_pool['queue_size']}, rejected={thread_pool['rejected_tasks']}",
    )
    cols[3].metric(
        "Datasource",
        f"{datasource['active_count']}/{datasource['max_pool_size']}",
        help=f"timeouts={datasource['timed_out_requests']}",
    )
    st.caption(
        f"Deployment {deployment['name']}: status={deployment['status']}, enabled={deployment['enabled']}"
    )


def render_monitoring() -> None:
    status = runtime_store.get_monitoring_status(settings.server_id)
    st.subheader("Polling status")
    cols = st.columns(5)
    cols[0].metric("Monitoring", status.status)
    cols[1].metric("Interval", f"{settings.poll_interval_seconds}s")
    cols[2].metric("Cursor", status.current_cursor)
    cols[3].metric("Last scan", status.last_scan_at or "—")
    cols[4].metric("Next scan", status.next_scan_at or "—")
    if status.last_error:
        st.error(status.last_error)


def render_controls() -> None:
    pending = runtime_store.list_pending_approvals()
    st.subheader("Controls")
    left, right = st.columns(2)

    if left.button("Run scan now", type="primary", use_container_width=True):
        with st.spinner("Running Monitoring Graph..."):
            run_async(service.run_monitoring_cycle())
        st.rerun()

    if right.button(
        "Inject Random Event",
        use_container_width=True,
        disabled=bool(pending),
        help="Ground Truth is hidden from the Agent and revealed only after completion.",
    ):
        event = injector.inject_random()
        st.session_state["last_injected_event_id"] = event.event_id
        runtime_store.add_activity(
            settings.server_id,
            "simulator",
            "Random simulator event injected; Ground Truth hidden from Agent",
        )
        st.success("Random event injected. Ground Truth remains hidden until evaluation is allowed.")

    with st.expander("Developer controls"):
        chosen = st.selectbox("Inject a specific Ground Truth scenario", SCENARIOS)
        if st.button("Inject selected scenario", disabled=bool(pending)):
            event = injector.inject(chosen)
            st.session_state["last_injected_event_id"] = event.event_id
            runtime_store.add_activity(
                settings.server_id,
                "simulator",
                "Developer-selected simulator event injected; label withheld from Agent",
            )
            st.success("Scenario injected. The Agent State still receives no Ground Truth label.")


def render_approvals() -> None:
    pending = runtime_store.list_pending_approvals()
    st.subheader("Human approval")
    if not pending:
        st.info("No pending LangGraph interrupt.")
        return

    for record in pending:
        payload = record.pending_approval or {}
        with st.container(border=True):
            st.markdown(f"**Incident `{record.incident_id}`**")
            c1, c2, c3 = st.columns(3)
            c1.write(f"Action: `{payload.get('action')}`")
            c2.write(f"Risk: **{payload.get('risk')}**")
            c3.write(f"Current → proposed: `{payload.get('current_value')}` → `{payload.get('proposed_value')}`")
            st.write(payload.get("reason") or "No reason supplied")

            approve, reject = st.columns(2)
            if approve.button("Approve", key=f"approve-{record.incident_id}", use_container_width=True):
                with st.spinner("Resuming the same LangGraph thread..."):
                    run_async(service.resume_incident(record.incident_id, decision="approve"))
                st.rerun()
            if reject.button("Reject", key=f"reject-{record.incident_id}", use_container_width=True):
                run_async(service.resume_incident(record.incident_id, decision="reject"))
                st.rerun()

            default_value = payload.get("proposed_value")
            if isinstance(default_value, int):
                edited = st.number_input(
                    "Edit proposed value",
                    value=default_value,
                    step=1,
                    key=f"edit-value-{record.incident_id}",
                )
                if st.button(
                    "Edit & Approve",
                    key=f"edit-approve-{record.incident_id}",
                    use_container_width=True,
                ):
                    run_async(
                        service.resume_incident(
                            record.incident_id,
                            decision="edit_and_approve",
                            proposed_value=int(edited),
                        )
                    )
                    st.rerun()


def render_incidents() -> None:
    incidents = runtime_store.list_incidents(limit=20)
    st.subheader("Incidents")
    if not incidents:
        st.info("No incidents yet.")
        return

    rows = [
        {
            "incident_id": item.incident_id,
            "status": item.status,
            "category": item.category,
            "severity": item.severity,
            "confidence": item.confidence,
            "tool_calls": item.investigation_tool_calls,
            "recovered": item.recovered,
            "created_at": item.created_at,
        }
        for item in incidents
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def ground_truth_is_revealable(event: GroundTruthEvent) -> bool:
    if event.linked_incident_id:
        record = runtime_store.get_incident(event.linked_incident_id)
        return bool(record and terminal(record))
    monitoring = runtime_store.get_monitoring_status(event.server_id)
    # If no incident was linked, the monitoring cycle itself is the completion
    # boundary. This reveals both a correct NORMAL decision and a false negative.
    return bool(monitoring.last_scan_at and monitoring.last_scan_at >= event.injected_at)


def render_ground_truth() -> None:
    st.subheader("Ground Truth comparison")
    event_id = st.session_state.get("last_injected_event_id")
    event = truth_store.get(event_id) if event_id else truth_store.latest(settings.server_id)
    if event is None:
        st.info("Inject an event to create Ground Truth.")
        return
    if not ground_truth_is_revealable(event):
        st.warning("Ground Truth is intentionally hidden while the Agent is still working.")
        return

    st.write(f"Injected: **{event.scenario}**")
    if event.linked_incident_id:
        record = runtime_store.get_incident(event.linked_incident_id)
        if record is None:
            return
        actual = normalize_diagnosis((record.diagnosis or {}).get("root_cause"))
        correct = actual == event.scenario
        detection = "False Positive" if event.scenario == "NORMAL_ACTIVITY" else "Detected"
        st.write(f"Detection: **{detection}**")
        st.write(f"Agent diagnosis: **{actual or 'N/A'}**")
        st.write(f"Diagnosis: **{'Correct' if correct else 'Incorrect'}**")
        st.write(f"Recovery: **{'Success' if record.recovered else 'Failed / not applicable'}**")
    else:
        st.write("Agent diagnosis: **No incident created**")
        st.write("Detection: **Correct**" if event.scenario == "NORMAL_ACTIVITY" else "Detection: **Missed**")


def render_activity() -> None:
    st.subheader("Agent activity timeline")
    rows = runtime_store.list_activity(settings.server_id, limit=80)
    if not rows:
        st.info("No activity recorded yet.")
        return
    rows.reverse()
    st.dataframe(
        [
            {
                "time": row["timestamp"],
                "incident": row["incident_id"] or "",
                "type": row["event_type"],
                "activity": row["message"],
            }
            for row in rows
        ],
        use_container_width=True,
        hide_index=True,
    )


def render_latest_evaluation() -> None:
    st.subheader("STEP 12 — Latest evaluation")
    path = Path(settings.evaluation_report_path)
    if not path.exists():
        st.caption("Run `make step12` to generate an evaluation report.")
        return
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        st.warning("Latest evaluation report could not be read.")
        return
    summary = report.get("summary", {})
    cols = st.columns(4)
    cols[0].metric("Detection accuracy", f"{float(summary.get('incident_detection_accuracy', 0)):.0%}")
    cols[1].metric("Diagnosis accuracy", f"{float(summary.get('diagnosis_accuracy', 0)):.0%}")
    cols[2].metric("Recovery success", f"{float(summary.get('recovery_success_rate', 0)):.0%}")
    cols[3].metric("Avg tool calls", f"{float(summary.get('average_investigation_tool_calls', 0)):.2f}")
    st.caption(
        f"False positives={summary.get('false_positive_count', 0)}, "
        f"false negatives={summary.get('false_negative_count', 0)}, runs={summary.get('runs', 0)}"
    )


st.set_page_config(page_title="LangGraph JBoss Agent", page_icon="🧭", layout="wide")
st.title("LangGraph JBoss Incident Response Agent")
st.caption("STEP 0–12 learning implementation — Scheduler / UI / Evaluation integrated")

render_server_snapshot()
render_monitoring()
render_controls()
render_approvals()
render_incidents()
render_ground_truth()
render_activity()
render_latest_evaluation()
