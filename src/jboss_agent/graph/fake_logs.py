"""Small deterministic log samples for STEP 1/2.

This is intentionally *not* the stateful Fake JBoss simulator from later steps.
The CLI chooses a sample, but only the raw log lines are passed to the graph.
No scenario label or ground truth is exposed to Gemini.
"""

from __future__ import annotations

from typing import Literal


LogScenario = Literal["normal", "thread_pool", "datasource_pool", "deployment", "unknown"]

DEFAULT_FAKE_LOG_LINES = [
    "2026-09-05 17:00:00 INFO  [org.jboss.as] WFLYSRV0025: JBoss EAP started",
    "2026-09-05 17:00:05 INFO  [org.example.App] health endpoint returned 200",
]

_LOG_SAMPLES: dict[LogScenario, list[str]] = {
    "normal": [
        "2026-09-05 17:10:00 INFO  [org.example.OrderService] request completed in 84ms",
        "2026-09-05 17:10:01 INFO  [org.example.OrderService] request completed in 91ms",
    ],
    "thread_pool": [
        "2026-09-05 17:11:00 WARN  [org.xnio] task rejected from executor default",
        "2026-09-05 17:11:01 ERROR [org.example.Api] request queue is growing; worker threads busy",
        "2026-09-05 17:11:02 WARN  [org.xnio] no worker thread available for request",
    ],
    "datasource_pool": [
        "2026-09-05 17:12:00 WARN  [org.jboss.jca] IJ000655: No managed connections available",
        "2026-09-05 17:12:01 ERROR [org.example.Dao] timeout waiting for JDBC connection from pool",
    ],
    "deployment": [
        "2026-09-05 17:13:00 ERROR [org.jboss.as.server] WFLYSRV0021: Deploy of deployment app.war was rolled back",
        "2026-09-05 17:13:01 ERROR [org.jboss.as.controller] required service jboss.deployment.unit.app.war is missing",
    ],
    "unknown": [
        "2026-09-05 17:14:00 ERROR [org.example.CustomSubsystem] ZXQ-991 unexpected subsystem state",
        "2026-09-05 17:14:01 WARN  [org.example.CustomSubsystem] operation aborted without known signature",
    ],
}


def get_log_sample(scenario: LogScenario) -> list[str]:
    """Return a copy so callers cannot mutate the module-level examples."""

    return list(_LOG_SAMPLES[scenario])
