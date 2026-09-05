"""APScheduler wrapper for STEP 10.

The scheduler contains no incident classification or remediation logic. Its job
is to invoke one application monitoring cycle at a fixed interval.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Protocol

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from jboss_agent.config import Settings, get_settings
from jboss_agent.runtime.store import RuntimeStore


logger = logging.getLogger(__name__)


class MonitoringCycle(Protocol):
    async def run_monitoring_cycle(self) -> dict[str, object]: ...


class MonitorScheduler:
    JOB_ID = "jboss-monitoring-cycle"

    def __init__(
        self,
        cycle: MonitoringCycle,
        *,
        settings: Settings | None = None,
        runtime_store: RuntimeStore | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cycle = cycle
        self.runtime_store = runtime_store or RuntimeStore(self.settings.runtime_db_path)
        self.scheduler = AsyncIOScheduler(timezone="UTC")

    async def _job(self) -> None:
        try:
            await self.cycle.run_monitoring_cycle()
        except Exception:
            logger.exception("scheduled monitoring cycle failed")
        finally:
            self._publish_next_run()

    def start(self, *, run_immediately: bool = True) -> None:
        job_kwargs: dict[str, object] = {}
        if run_immediately:
            # In APScheduler 3.x, explicitly passing ``next_run_time=None``
            # pauses a job. Omit the argument when we want the normal interval
            # trigger to calculate the first execution time.
            job_kwargs["next_run_time"] = datetime.now(timezone.utc)

        self.scheduler.add_job(
            self._job,
            trigger="interval",
            seconds=self.settings.poll_interval_seconds,
            id=self.JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            **job_kwargs,
        )
        self.scheduler.start()
        self._publish_next_run()
        logger.info(
            "Scheduler started interval=%ss thread_id=%s",
            self.settings.poll_interval_seconds,
            self.settings.monitoring_thread_id,
        )

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def _publish_next_run(self) -> None:
        job = self.scheduler.get_job(self.JOB_ID)
        next_run = None if job is None or job.next_run_time is None else job.next_run_time.isoformat()
        self.runtime_store.set_next_scan(self.settings.server_id, next_run)


async def run_forever(cycle: MonitoringCycle, *, settings: Settings | None = None) -> None:
    resolved = settings or get_settings()
    scheduler = MonitorScheduler(cycle, settings=resolved)
    scheduler.start(run_immediately=True)
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown()
