"""Application orchestration for STEP 10-12.

The scheduler calls ``run_monitoring_cycle``. Streamlit calls the same method for
"Run scan now" and ``resume_incident`` for HITL. Business decisions remain in
LangGraph/domain nodes; this service only connects the two graphs and persists
UI metadata.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langgraph.types import Command

from jboss_agent.config import Settings, get_settings
from jboss_agent.graph.incident_graph import build_step9_graph
from jboss_agent.graph.operational_monitoring_graph import build_operational_monitoring_graph
from jboss_agent.mcp_client.client import load_fake_jboss_read_write_tools
from jboss_agent.mcp_client.tool_registry import READ_ONLY_JBOSS_TOOL_NAMES
from jboss_agent.persistence.checkpointer import open_durable_checkpointer
from jboss_agent.runtime.store import RuntimeStore
from jboss_agent.simulator.ground_truth import GroundTruthStore


class OperationalAgentService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        runtime_store: RuntimeStore | None = None,
        truth_store: GroundTruthStore | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.runtime_store = runtime_store or RuntimeStore(self.settings.runtime_db_path)
        self.truth_store = truth_store or GroundTruthStore(self.settings.simulator_db_path)

    async def run_monitoring_cycle(self) -> dict[str, Any]:
        """Run one scan and start a newly detected incident until END/interrupt."""
        server_id = self.settings.server_id
        self.runtime_store.begin_scan(server_id)

        try:
            _client, read_tools, write_tools = await load_fake_jboss_read_write_tools()
            async with open_durable_checkpointer(self.settings) as checkpointer:
                monitor_graph = build_operational_monitoring_graph(
                    read_tools,
                    checkpointer=checkpointer,
                    settings=self.settings,
                )
                monitor_config = {
                    "configurable": {"thread_id": self.settings.monitoring_thread_id}
                }
                monitoring = await monitor_graph.ainvoke(
                    {"server_id": server_id}, config=monitor_config
                )

                incident_id = monitoring.get("incident_id")
                self.runtime_store.complete_scan(
                    server_id,
                    previous_cursor=int(monitoring.get("scan_from_cursor", 0)),
                    current_cursor=int(monitoring.get("current_log_cursor", 0)),
                    incident_id=str(incident_id) if incident_id else None,
                )
                self._record_monitoring_activity(monitoring)

                if not incident_id:
                    return {"monitoring": monitoring, "incident": None}

                incident_id = str(incident_id)
                incident_thread_id = f"incident:{incident_id}"
                self.runtime_store.upsert_incident(
                    incident_id=incident_id,
                    thread_id=incident_thread_id,
                    server_id=server_id,
                    category=str(monitoring.get("category", "UNKNOWN")),
                    severity=str(monitoring.get("severity", "MEDIUM")),
                    confidence=float(monitoring.get("confidence", 0.0)),
                    summary=str(monitoring.get("summary", "Incident detected")),
                    status="INVESTIGATING",
                )
                # Link by ID only. The hidden scenario value is never read here.
                self.truth_store.link_latest_unlinked(server_id, incident_id)
                self.runtime_store.add_activity(
                    server_id,
                    "incident",
                    f"Incident {incident_id} created; starting read-only investigation",
                    incident_id=incident_id,
                )

                incident_graph = build_step9_graph(
                    read_tools,
                    write_tools,
                    checkpointer=checkpointer,
                    settings=self.settings,
                )
                initial = {
                    "incident_id": incident_id,
                    "server_id": server_id,
                    "category": str(monitoring.get("category", "UNKNOWN")),
                    "severity": str(monitoring.get("severity", "MEDIUM")),
                    "confidence": float(monitoring.get("confidence", 0.0)),
                    "initial_log_lines": list(monitoring.get("new_log_lines", [])),
                    "messages": [],
                    "evidence": [],
                    "investigation_count": 0,
                    "recovery_attempts": 0,
                    "node_trace": [],
                }
                incident = await incident_graph.ainvoke(
                    initial,
                    config={"configurable": {"thread_id": incident_thread_id}},
                )
                self._persist_incident_result(monitoring, incident, incident_thread_id)
                return {"monitoring": monitoring, "incident": incident}
        except Exception as exc:
            self.runtime_store.fail_scan(server_id, str(exc))
            raise

    async def resume_incident(
        self,
        incident_id: str,
        *,
        decision: str,
        proposed_value: int | None = None,
    ) -> dict[str, Any]:
        record = self.runtime_store.get_incident(incident_id)
        if record is None:
            raise ValueError(f"unknown incident_id: {incident_id}")

        payload: dict[str, Any] = {"decision": decision}
        if proposed_value is not None:
            payload["proposed_value"] = proposed_value

        _client, read_tools, write_tools = await load_fake_jboss_read_write_tools()
        async with open_durable_checkpointer(self.settings) as checkpointer:
            graph = build_step9_graph(
                read_tools,
                write_tools,
                checkpointer=checkpointer,
                settings=self.settings,
            )
            result = await graph.ainvoke(
                Command(resume=payload),
                config={"configurable": {"thread_id": record.thread_id}},
            )

        monitoring_stub = {
            "incident_id": record.incident_id,
            "server_id": record.server_id,
            "category": record.category,
            "severity": record.severity,
            "confidence": record.confidence,
            "summary": record.summary,
        }
        self._persist_incident_result(monitoring_stub, result, record.thread_id)
        return result

    def _record_monitoring_activity(self, state: dict[str, Any]) -> None:
        server_id = self.settings.server_id
        lines = len(state.get("new_log_lines", []))
        if state.get("cursor_reset_detected"):
            self.runtime_store.add_activity(
                server_id,
                "monitoring",
                "Log cursor was beyond EOF; treated as log reset/rotation and restarted at cursor 0",
            )
        if not state.get("has_new_logs"):
            message = "No new server.log lines; Gemini skipped"
        elif state.get("incident_detected"):
            message = (
                f"{lines} new log lines analyzed; incident suspected: "
                f"{state.get('category')} ({float(state.get('confidence', 0.0)):.0%})"
            )
        else:
            message = f"{lines} new log lines analyzed; no incident detected"
        self.runtime_store.add_activity(server_id, "monitoring", message)

    def _persist_incident_result(
        self,
        monitoring: dict[str, Any],
        result: dict[str, Any],
        thread_id: str,
    ) -> None:
        incident_id = str(monitoring["incident_id"])
        pending = _interrupt_payload(result)
        proposed_action = result.get("proposed_action")
        diagnosis = result.get("diagnosis")
        recovered = result.get("recovered")
        approval = result.get("approval_status")
        failure_reason = result.get("failure_reason")

        if pending is not None:
            status = "PENDING_APPROVAL"
            activity = "Investigation paused for human approval"
        elif approval == "REJECTED":
            status = "REJECTED"
            activity = "Human rejected remediation; no write executed"
        elif approval == "BLOCKED":
            status = "BLOCKED"
            activity = "Remediation blocked by policy"
        elif recovered is True:
            action_type = (proposed_action or {}).get("type")
            status = "RESOLVED_NO_ACTION" if action_type == "NONE" else "RECOVERED"
            activity = "Incident workflow completed successfully"
        elif recovered is False:
            status = "FAILED_SAFE"
            activity = "Recovery failed; fail-safe escalation reached"
        else:
            status = "COMPLETED"
            activity = "Incident workflow completed"

        read_tool_names = _read_tool_names(result.get("messages", []))
        tool_calls = len(read_tool_names)
        self.runtime_store.upsert_incident(
            incident_id=incident_id,
            thread_id=thread_id,
            server_id=str(monitoring["server_id"]),
            category=str(monitoring.get("category", "UNKNOWN")),
            severity=str(monitoring.get("severity", "MEDIUM")),
            confidence=float(monitoring.get("confidence", 0.0)),
            summary=str(monitoring.get("summary", "Incident detected")),
            status=status,
            pending_approval=pending,
            diagnosis=diagnosis if isinstance(diagnosis, dict) else None,
            proposed_action=proposed_action if isinstance(proposed_action, dict) else None,
            recovered=recovered if isinstance(recovered, bool) else None,
            failure_reason=str(failure_reason) if failure_reason else None,
            investigation_tool_calls=tool_calls,
        )
        server_id = str(monitoring["server_id"])
        if read_tool_names:
            self.runtime_store.add_activity(
                server_id,
                "tool",
                "Read MCP tools: " + ", ".join(read_tool_names),
                incident_id=incident_id,
            )
        if isinstance(diagnosis, dict):
            confidence = diagnosis.get("confidence")
            suffix = f" ({float(confidence):.0%})" if isinstance(confidence, (int, float)) else ""
            self.runtime_store.add_activity(
                server_id,
                "diagnosis",
                f"Diagnosis: {diagnosis.get('root_cause', 'UNKNOWN')}{suffix}",
                incident_id=incident_id,
            )
        execution = result.get("execution_result")
        if isinstance(execution, dict) and execution.get("tool_name"):
            self.runtime_store.add_activity(
                server_id,
                "write_tool",
                f"Executed approved MCP write tool: {execution['tool_name']}",
                incident_id=incident_id,
            )
        self.runtime_store.add_activity(
            server_id,
            "incident",
            activity,
            incident_id=incident_id,
            details={"status": status, "tool_calls": tool_calls},
        )


def _interrupt_payload(result: dict[str, Any]) -> dict[str, Any] | None:
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0]
    value = getattr(first, "value", first)
    return dict(value) if isinstance(value, dict) else {"value": value}


def _read_tool_names(messages: list[Any]) -> list[str]:
    names: list[str] = []
    for message in messages:
        if not isinstance(message, AIMessage):
            continue
        for call in message.tool_calls:
            name = str(call.get("name", ""))
            if name in READ_ONLY_JBOSS_TOOL_NAMES:
                names.append(name)
    return names
