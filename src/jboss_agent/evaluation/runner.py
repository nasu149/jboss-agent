"""STEP 12 random-event evaluation harness."""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from jboss_agent.config import Settings, get_settings
from jboss_agent.evaluation.metrics import EvaluationTrial, build_trial, summarize_trials
from jboss_agent.graph.incident_graph import build_step9_graph
from jboss_agent.graph.operational_monitoring_graph import build_operational_monitoring_graph
from jboss_agent.jboss.fake_operations import FakeJBossOperations
from jboss_agent.mcp_client.client import load_fake_jboss_read_write_tools
from jboss_agent.mcp_client.tool_registry import READ_ONLY_JBOSS_TOOL_NAMES
from jboss_agent.simulator.fault_injector import FaultInjector
from jboss_agent.simulator.ground_truth import GroundTruthStore
from jboss_agent.simulator.scenarios import GroundTruthScenario, SCENARIOS


class EvaluationRunner:
    """Exercise the real Gemini + MCP graphs while keeping Ground Truth external."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.fake = FakeJBossOperations(
            self.settings.fake_jboss_data_dir,
            server_id=self.settings.server_id,
        )
        truth_path = Path(self.settings.evaluation_report_path).with_suffix(".truth.sqlite")
        self.truth_store = GroundTruthStore(truth_path)
        self.injector = FaultInjector(self.fake, self.truth_store)

    async def run(self, *, runs: int | None = None, seed: int | None = None) -> dict[str, Any]:
        run_count = runs or self.settings.evaluation_runs
        if not 10 <= run_count <= 30:
            raise ValueError("STEP 12 evaluation runs must be between 10 and 30")
        resolved_seed = self.settings.evaluation_seed if seed is None else seed
        scenarios = _balanced_scenarios(run_count, resolved_seed)

        self.truth_store.clear()
        _client, read_tools, write_tools = await load_fake_jboss_read_write_tools()
        checkpointer = InMemorySaver()
        monitor_graph = build_operational_monitoring_graph(
            read_tools,
            checkpointer=checkpointer,
            settings=self.settings,
            notifier=_evaluation_notifier,
        )
        incident_graph = build_step9_graph(
            read_tools,
            write_tools,
            checkpointer=checkpointer,
            settings=self.settings,
        )

        trials: list[EvaluationTrial] = []
        for index, scenario in enumerate(scenarios, start=1):
            self.fake.reset(include_boot_logs=False)
            event = self.injector.inject(scenario)
            monitor_thread = f"eval:{resolved_seed}:monitor:{index}:{event.event_id}"
            monitoring = await monitor_graph.ainvoke(
                {"server_id": self.settings.server_id},
                config={"configurable": {"thread_id": monitor_thread}},
            )

            incident_id_raw = monitoring.get("incident_id")
            incident_detected = bool(incident_id_raw)
            diagnosis: str | None = None
            recovered = scenario == "NORMAL_ACTIVITY" and not incident_detected
            rejected = False
            tool_calls = 0
            incident_id = str(incident_id_raw) if incident_id_raw else None

            if incident_id:
                thread_id = f"eval:incident:{incident_id}:{index}"
                result = await incident_graph.ainvoke(
                    {
                        "incident_id": incident_id,
                        "server_id": self.settings.server_id,
                        "category": str(monitoring.get("category", "UNKNOWN")),
                        "severity": str(monitoring.get("severity", "MEDIUM")),
                        "confidence": float(monitoring.get("confidence", 0.0)),
                        "initial_log_lines": list(monitoring.get("new_log_lines", [])),
                        "messages": [],
                        "evidence": [],
                        "investigation_count": 0,
                        "recovery_attempts": 0,
                        "node_trace": [],
                    },
                    config={"configurable": {"thread_id": thread_id}},
                )
                while result.get("__interrupt__"):
                    result = await incident_graph.ainvoke(
                        Command(resume={"decision": "approve"}),
                        config={"configurable": {"thread_id": thread_id}},
                    )
                diagnosis_obj = result.get("diagnosis") or {}
                if isinstance(diagnosis_obj, dict):
                    diagnosis = str(diagnosis_obj.get("root_cause") or "") or None
                # Score recovery from the simulator's observable final state rather
                # than trusting the Agent's own `recovered` flag. This prevents a
                # self-reported success from inflating the evaluation metric.
                recovered = self._ground_truth_recovery_check(scenario)
                rejected = result.get("approval_status") == "REJECTED"
                tool_calls = _count_tool_calls(result.get("messages", []))

            trials.append(
                build_trial(
                    trial=index,
                    ground_truth=scenario,
                    incident_detected=incident_detected,
                    diagnosis=diagnosis,
                    recovered=recovered,
                    human_rejected=rejected,
                    investigation_tool_calls=tool_calls,
                    incident_id=incident_id,
                )
            )

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "seed": resolved_seed,
            "summary": summarize_trials(trials),
            "trials": [trial.as_dict() for trial in trials],
        }
        path = Path(self.settings.evaluation_report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        # Do not leave the shared Fake JBoss in the final random fault state.
        self.fake.reset(include_boot_logs=True)
        return report

    def _ground_truth_recovery_check(self, scenario: GroundTruthScenario) -> bool:
        health = self.fake.get_server_health(self.settings.server_id)
        base = health.get("status") == "UP" and float(health.get("request_error_rate", 1.0)) < 0.05
        if not base:
            return False
        if scenario == "THREAD_POOL_CONFIGURATION":
            pool = self.fake.get_thread_pool_status(self.settings.server_id)
            return (
                int(pool["active_threads"]) <= int(pool["max_threads"])
                and int(pool["queue_size"]) == 0
                and int(pool["rejected_tasks"]) == 0
            )
        if scenario == "DATASOURCE_POOL_EXHAUSTION":
            ds = self.fake.get_datasource_status(self.settings.server_id)
            return (
                int(ds["active_count"]) <= int(ds["max_pool_size"])
                and int(ds["timed_out_requests"]) == 0
            )
        if scenario == "DEPLOYMENT_FAILURE":
            deployment = self.fake.get_deployment_status(self.settings.server_id)
            return deployment.get("status") == "OK" and bool(deployment.get("enabled"))
        return True


def _balanced_scenarios(runs: int, seed: int) -> list[GroundTruthScenario]:
    rng = random.Random(seed)
    values: list[GroundTruthScenario] = []
    while len(values) < runs:
        batch = list(SCENARIOS)
        rng.shuffle(batch)
        values.extend(batch)
    return values[:runs]


def _evaluation_notifier(payload: dict[str, object]) -> str:
    """Never send real Teams traffic from a 10-30 trial evaluation run."""
    return json.dumps(
        {
            "success": True,
            "status": "evaluation_dry_run",
            "incident_id": payload.get("incident_id"),
        }
    )


def _count_tool_calls(messages: list[Any]) -> int:
    return sum(
        1
        for message in messages
        if isinstance(message, AIMessage)
        for call in message.tool_calls
        if call.get("name") in READ_ONLY_JBOSS_TOOL_NAMES
    )
