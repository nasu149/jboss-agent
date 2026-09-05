"""Small scenario setup helpers used by CLI demos.

The function names are ground truth, but they are called outside the Graph. The
Agent receives only log text and MCP-observable server state.
"""

from __future__ import annotations

from jboss_agent.jboss.fake_operations import FakeJBossOperations


def seed_thread_pool_configuration_incident(fake: FakeJBossOperations) -> list[str]:
    fake.reset(include_boot_logs=True)
    # Simulate an operator/config deployment reducing capacity before the incident.
    fake.set_thread_pool_max_threads(fake.server_id, 20)
    fake.simulate_thread_pool_load(
        active_threads=20,
        queue_size=37,
        rejected_tasks=11,
        error_rate=0.24,
    )
    lines = [
        "2026-09-05 18:10:01 WARN  [org.example.web] request queue is growing",
        "2026-09-05 18:10:02 ERROR [org.example.web] task rejected while serving request",
        "2026-09-05 18:10:03 WARN  [org.example.web] intermittent HTTP 503 responses observed",
    ]
    fake.append_log_lines(lines)
    return lines
