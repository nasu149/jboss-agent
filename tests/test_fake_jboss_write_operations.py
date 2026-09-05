from pathlib import Path

import pytest

from jboss_agent.jboss.fake_operations import FakeJBossOperations


def test_thread_pool_write_is_validated_idempotent_and_drains_backlog(tmp_path: Path) -> None:
    fake = FakeJBossOperations(tmp_path / "fake", server_id="jboss-test")
    fake.reset(include_boot_logs=False)
    fake.set_thread_pool_max_threads("jboss-test", 20)
    fake.simulate_thread_pool_load(active_threads=20, queue_size=10, rejected_tasks=3)

    first = fake.set_thread_pool_max_threads("jboss-test", 80)
    second = fake.set_thread_pool_max_threads("jboss-test", 80)
    status = fake.get_thread_pool_status("jboss-test")

    assert first["changed"] is True
    assert second["changed"] is False
    assert status["max_threads"] == 80
    assert status["queue_size"] == 0
    assert status["rejected_tasks"] == 0


def test_thread_pool_write_rejects_out_of_range_value(tmp_path: Path) -> None:
    fake = FakeJBossOperations(tmp_path / "fake", server_id="jboss-test")
    fake.reset(include_boot_logs=False)
    with pytest.raises(ValueError, match="1-200"):
        fake.set_thread_pool_max_threads("jboss-test", 201)
