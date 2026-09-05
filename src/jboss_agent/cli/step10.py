"""STEP 10 CLI: APScheduler outside the LangGraph workflows."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from jboss_agent.config import get_settings
from jboss_agent.runtime.service import OperationalAgentService
from jboss_agent.scheduler.monitor_scheduler import run_forever


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run STEP 10 scheduled monitoring")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one monitoring cycle and exit (useful for learning/testing).",
    )
    return parser.parse_args()


async def _run() -> None:
    args = _args()
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    service = OperationalAgentService(settings)

    print(f"monitor_thread_id={settings.monitoring_thread_id}")
    print(f"poll_interval_seconds={settings.poll_interval_seconds}")
    print(f"checkpoint_db={settings.checkpoint_db_path}")

    if args.once:
        result = await service.run_monitoring_cycle()
        monitoring = result["monitoring"]
        print(
            json.dumps(
                {
                    "has_new_logs": monitoring.get("has_new_logs"),
                    "scan_from_cursor": monitoring.get("scan_from_cursor"),
                    "current_log_cursor": monitoring.get("current_log_cursor"),
                    "incident_id": monitoring.get("incident_id"),
                    "category": monitoring.get("category"),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        return

    print("APScheduler running. Press Ctrl+C to stop.")
    await run_forever(service, settings=settings)


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("Scheduler stopped.")


if __name__ == "__main__":
    main()
