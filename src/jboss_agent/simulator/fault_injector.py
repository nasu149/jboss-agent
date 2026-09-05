"""Stateful Fake JBoss fault injector kept completely outside Agent-visible State."""

from __future__ import annotations

import random
import uuid

from jboss_agent.jboss.fake_operations import FakeJBossOperations
from jboss_agent.simulator.ground_truth import GroundTruthEvent, GroundTruthStore
from jboss_agent.simulator.scenarios import GroundTruthScenario, SCENARIOS


class FaultInjector:
    def __init__(self, fake: FakeJBossOperations, truth_store: GroundTruthStore) -> None:
        self.fake = fake
        self.truth_store = truth_store

    def inject_random(self, *, rng: random.Random | None = None) -> GroundTruthEvent:
        chooser = rng or random.SystemRandom()
        scenario = chooser.choice(SCENARIOS)
        return self.inject(scenario)

    def inject(self, scenario: GroundTruthScenario) -> GroundTruthEvent:
        event_id = f"evt-{uuid.uuid4().hex[:10]}"
        self.fake.ensure_initialized()

        if scenario == "THREAD_POOL_CONFIGURATION":
            self.fake.set_thread_pool_max_threads(self.fake.server_id, 20)
            self.fake.simulate_thread_pool_load(
                active_threads=20,
                queue_size=37,
                rejected_tasks=11,
                error_rate=0.24,
            )
            self.fake.append_log_lines(
                [
                    "2026-09-05 18:20:01 WARN  [org.example.web] HTTP worker queue growth detected",
                    "2026-09-05 18:20:02 ERROR [org.example.web] task rejected from worker executor",
                    "2026-09-05 18:20:03 WARN  [org.example.web] HTTP 503 responses increased",
                ]
            )
        elif scenario == "DATASOURCE_POOL_EXHAUSTION":
            self.fake.set_datasource_max_pool_size(self.fake.server_id, 5)
            self.fake.simulate_datasource_load(
                active_count=5,
                timed_out_requests=14,
                error_rate=0.28,
            )
            self.fake.append_log_lines(
                [
                    "2026-09-05 18:21:01 WARN  [org.jboss.jca] datasource pool has no available connection",
                    "2026-09-05 18:21:02 ERROR [org.example.dao] timed out waiting for ExampleDS connection",
                    "2026-09-05 18:21:03 WARN  [org.example.api] database-backed requests returning 503",
                ]
            )
        elif scenario == "DEPLOYMENT_FAILURE":
            self.fake.simulate_deployment_failure("app.war")
            self.fake.append_log_lines(
                [
                    "2026-09-05 18:22:01 ERROR [org.jboss.as.server] deployment app.war failed to start",
                    "2026-09-05 18:22:02 ERROR [org.example.App] application endpoint unavailable",
                    "2026-09-05 18:22:03 WARN  [org.example.health] readiness check returned 503",
                ]
            )
        elif scenario == "NORMAL_ACTIVITY":
            self.fake.append_log_lines(
                [
                    "2026-09-05 18:23:01 INFO  [org.example.web] request completed status=200 elapsed=42ms",
                    "2026-09-05 18:23:02 INFO  [org.example.jobs] scheduled cleanup completed",
                    "2026-09-05 18:23:03 INFO  [org.example.health] readiness check returned 200",
                ]
            )
        else:  # pragma: no cover - protected by Literal/type checker
            raise ValueError(f"unsupported scenario: {scenario}")

        return self.truth_store.record(event_id, self.fake.server_id, scenario)
