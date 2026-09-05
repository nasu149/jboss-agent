from pathlib import Path

import pytest

from jboss_agent.jboss.fake_operations import FakeJBossOperations


def test_read_server_log_returns_only_bytes_after_cursor(tmp_path: Path) -> None:
    fake = FakeJBossOperations(tmp_path / "fake", server_id="jboss-test")
    fake.reset(include_boot_logs=False)

    first_append = fake.append_log_lines(["line-1", "line-2"])
    first = fake.read_server_log("jboss-test", 0)

    assert first["lines"] == ["line-1", "line-2"]
    assert first["to_cursor"] == first_append["to_cursor"]

    cursor = int(first["to_cursor"])
    no_change = fake.read_server_log("jboss-test", cursor)
    assert no_change["lines"] == []
    assert no_change["from_cursor"] == no_change["to_cursor"] == cursor

    fake.append_log_lines(["line-3"])
    delta = fake.read_server_log("jboss-test", cursor)
    assert delta["lines"] == ["line-3"]
    assert int(delta["to_cursor"]) > cursor


def test_read_server_log_rejects_cursor_beyond_file(tmp_path: Path) -> None:
    fake = FakeJBossOperations(tmp_path / "fake", server_id="jboss-test")
    fake.reset(include_boot_logs=False)

    with pytest.raises(ValueError, match="beyond current log size"):
        fake.read_server_log("jboss-test", 999)


def test_fake_status_reads_are_read_only_and_named(tmp_path: Path) -> None:
    fake = FakeJBossOperations(tmp_path / "fake", server_id="jboss-test")
    fake.reset()

    assert fake.get_server_health("jboss-test")["status"] == "UP"
    assert fake.get_thread_pool_status("jboss-test")["max_threads"] == 80
    assert fake.get_datasource_status("jboss-test")["max_pool_size"] == 30
    assert fake.get_deployment_status("jboss-test")["status"] == "OK"
    assert fake.get_recent_config_changes("jboss-test")["changes"] == []
