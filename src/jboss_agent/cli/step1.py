"""CLI runner for STEP 1."""

from __future__ import annotations

import json

from jboss_agent.graph.core_graph import build_step1_graph


def main() -> None:
    graph = build_step1_graph()
    result = graph.invoke({})

    print("STEP 1 graph: START -> collect_fake_log -> simple_check -> END")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
