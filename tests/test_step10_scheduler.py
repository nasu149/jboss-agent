from __future__ import annotations

import pytest

from jboss_agent.config import Settings
from jboss_agent.runtime.store import RuntimeStore
from jboss_agent.scheduler.monitor_scheduler import MonitorScheduler


class FakeCycle:
    async def run_monitoring_cycle(self) -> dict[str, object]:
        return {"ok": True}


@pytest.mark.asyncio
async def test_scheduler_owns_interval_not_graph(tmp_path) -> None:
    settings = Settings(
        POLL_INTERVAL_SECONDS=7,
        SERVER_ID="jboss-test",
        RUNTIME_DB_PATH=str(tmp_path / "runtime.sqlite"),
        _env_file=None,
    )
    store = RuntimeStore(settings.runtime_db_path)
    scheduler = MonitorScheduler(FakeCycle(), settings=settings, runtime_store=store)
    scheduler.start(run_immediately=False)
    try:
        job = scheduler.scheduler.get_job(MonitorScheduler.JOB_ID)
        assert job is not None
        assert int(job.trigger.interval.total_seconds()) == 7
        assert settings.monitoring_thread_id == "monitor:jboss-test"
    finally:
        scheduler.shutdown()
