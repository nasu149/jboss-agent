"""CLI runner for STEP 3 cursor-based monitoring."""

from __future__ import annotations

import json

from jboss_agent.config import get_settings
from jboss_agent.graph.cursor_monitoring_graph import build_step3_graph
from jboss_agent.graph.fake_logs import get_log_sample
from jboss_agent.jboss.fake_operations import FakeJBossOperations


def _print_run(label: str, result: dict[str, object]) -> None:
    summary = {
        "previous_log_cursor": result.get("previous_log_cursor"),
        "current_log_cursor": result.get("current_log_cursor"),
        "new_log_lines": result.get("new_log_lines"),
        "has_new_logs": result.get("has_new_logs"),
        "category": result.get("category"),
        "route_taken": result.get("route_taken"),
        "node_trace": result.get("node_trace"),
    }
    print(f"\n--- {label} ---")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    settings = get_settings()
    fake = FakeJBossOperations(settings.fake_jboss_data_dir, server_id=settings.server_id)
    fake.reset(include_boot_logs=False)
    graph = build_step3_graph(settings=settings, reader=fake)

    fake.append_log_lines(get_log_sample("normal"))
    first = graph.invoke({"server_id": settings.server_id, "previous_log_cursor": 0})
    _print_run("1. normal delta -> Gemini is invoked", first)

    first_cursor = int(first["current_log_cursor"])
    second = graph.invoke(
        {"server_id": settings.server_id, "previous_log_cursor": first_cursor}
    )
    _print_run("2. no delta -> Gemini is skipped", second)

    fake.append_log_lines(get_log_sample("thread_pool"))
    third = graph.invoke(
        {"server_id": settings.server_id, "previous_log_cursor": first_cursor}
    )
    _print_run("3. only newly appended thread-pool logs are analyzed", third)


if __name__ == "__main__":
    main()
