"""CLI runner for STEP 2 using the real Gemini structured-output classifier."""

from __future__ import annotations

import argparse
import json

from jboss_agent.graph.fake_logs import LogScenario, get_log_sample
from jboss_agent.graph.monitoring_graph import build_step2_graph

_SCENARIOS: tuple[LogScenario, ...] = (
    "normal",
    "thread_pool",
    "datasource_pool",
    "deployment",
    "unknown",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the STEP 2 LangGraph routing demo")
    parser.add_argument(
        "--scenario",
        choices=_SCENARIOS,
        default="thread_pool",
        help="Select raw fake log lines. The scenario label itself is not passed to Gemini.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    log_lines = get_log_sample(args.scenario)
    graph = build_step2_graph()
    result = graph.invoke({"input_log_lines": log_lines})

    print("STEP 2 graph: START -> collect_fake_log -> analyze_logs -> conditional branch -> END")
    print(f"input_sample={args.scenario} (label is CLI-only; Gemini receives raw logs)")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
