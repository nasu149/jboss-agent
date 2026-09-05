from __future__ import annotations

from jboss_agent.jboss.fake_operations import FakeJBossOperations
from jboss_agent.simulator.fault_injector import FaultInjector
from jboss_agent.simulator.ground_truth import GroundTruthStore


def test_ground_truth_is_separate_from_fake_jboss_state(tmp_path) -> None:
    fake = FakeJBossOperations(tmp_path / "jboss", server_id="jboss-test")
    truth = GroundTruthStore(tmp_path / "truth.sqlite")
    event = FaultInjector(fake, truth).inject("THREAD_POOL_CONFIGURATION")

    state_text = fake.state_path.read_text(encoding="utf-8")
    assert "THREAD_POOL_CONFIGURATION" not in state_text
    assert truth.get(event.event_id).scenario == "THREAD_POOL_CONFIGURATION"
    pool = fake.get_thread_pool_status("jboss-test")
    assert pool["max_threads"] == 20
    assert pool["queue_size"] > 0


def test_normal_activity_only_appends_info_logs(tmp_path) -> None:
    fake = FakeJBossOperations(tmp_path / "jboss", server_id="jboss-test")
    truth = GroundTruthStore(tmp_path / "truth.sqlite")
    fake.reset(include_boot_logs=False)
    event = FaultInjector(fake, truth).inject("NORMAL_ACTIVITY")
    log = fake.read_server_log("jboss-test", 0)
    assert event.scenario == "NORMAL_ACTIVITY"
    assert log["lines"]
    assert all("INFO" in line for line in log["lines"])
    assert fake.get_server_health("jboss-test")["request_error_rate"] == 0.0
