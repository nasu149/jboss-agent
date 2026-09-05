"""CLI runner for STEP 12 evaluation."""

from __future__ import annotations

import argparse
import asyncio
import json

from jboss_agent.config import get_settings
from jboss_agent.evaluation.runner import EvaluationRunner


def _args() -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run STEP 12 agent evaluation")
    parser.add_argument("--runs", type=int, default=settings.evaluation_runs)
    parser.add_argument("--seed", type=int, default=settings.evaluation_seed)
    return parser.parse_args()


async def _run() -> None:
    args = _args()
    report = await EvaluationRunner().run(runs=args.runs, seed=args.seed)
    print("STEP 12 evaluation summary")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"report={get_settings().evaluation_report_path}")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
