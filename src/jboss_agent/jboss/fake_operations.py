"""File-backed Fake JBoss operations used by STEP 3 and the STEP 5 MCP server.

The fake implementation intentionally keeps its state on disk. That gives us two
useful properties for later learning steps:

* the monitoring cursor refers to a real byte position in ``server.log``;
* an MCP server started as a separate stdio subprocess can observe the same fake
  JBoss state as the LangGraph process.

Ground truth is deliberately not stored here. Later Fault Simulator code owns
that information so the Agent-visible JBoss capability never leaks the answer.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


_DEFAULT_STATE: dict[str, Any] = {
    "server_id": "jboss-01",
    "health": {
        "status": "UP",
        "cpu_percent": 34.0,
        "heap_used_percent": 41.0,
        "request_error_rate": 0.0,
    },
    "thread_pool": {
        "name": "default",
        "max_threads": 80,
        "active_threads": 12,
        "queue_size": 0,
        "rejected_tasks": 0,
    },
    "datasource": {
        "name": "ExampleDS",
        "max_pool_size": 30,
        "active_count": 8,
        "available_count": 22,
        "timed_out_requests": 0,
    },
    "deployment": {
        "name": "app.war",
        "status": "OK",
        "enabled": True,
    },
    "recent_config_changes": [],
}

_DEFAULT_BOOT_LOGS = [
    "2026-09-05 17:00:00 INFO  [org.jboss.as] WFLYSRV0025: JBoss EAP started",
    "2026-09-05 17:00:05 INFO  [org.example.App] health endpoint returned 200",
]


class FakeJBossOperations:
    """Deterministic, file-backed subset of JBoss read operations.

    ``cursor`` is a UTF-8 byte offset, not a line number. This mirrors how real
    tail/read APIs often track an opaque file position and makes the cost-saving
    property of incremental reads easy to observe.
    """

    def __init__(self, data_dir: str | Path, *, server_id: str = "jboss-01") -> None:
        self.data_dir = Path(data_dir)
        self.server_id = server_id
        self.log_path = self.data_dir / "server.log"
        self.state_path = self.data_dir / "state.json"
        self._lock = Lock()

    def ensure_initialized(self) -> None:
        """Create default fake files if they do not exist yet."""

        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            state = json.loads(json.dumps(_DEFAULT_STATE))
            state["server_id"] = self.server_id
            self._write_state(state)
        if not self.log_path.exists():
            self.log_path.write_text("", encoding="utf-8")
            self.append_log_lines(_DEFAULT_BOOT_LOGS)

    def reset(self, *, include_boot_logs: bool = True) -> None:
        """Reset the fake JBoss state for a repeatable demo/test run."""

        self.data_dir.mkdir(parents=True, exist_ok=True)
        state = json.loads(json.dumps(_DEFAULT_STATE))
        state["server_id"] = self.server_id
        self._write_state(state)
        self.log_path.write_text("", encoding="utf-8")
        if include_boot_logs:
            self.append_log_lines(_DEFAULT_BOOT_LOGS)

    def append_log_lines(self, lines: list[str]) -> dict[str, int]:
        """Append log lines and return the byte cursor before and after append."""

        self.ensure_initialized_without_logs_if_needed()
        with self._lock:
            from_cursor = self.log_path.stat().st_size
            if lines:
                with self.log_path.open("ab") as stream:
                    for line in lines:
                        stream.write(line.rstrip("\n").encode("utf-8"))
                        stream.write(b"\n")
            to_cursor = self.log_path.stat().st_size
        return {"from_cursor": from_cursor, "to_cursor": to_cursor}

    def read_server_log(self, server_id: str, cursor: int) -> dict[str, object]:
        """Read only bytes added after ``cursor`` and return the new cursor."""

        self._validate_server_id(server_id)
        self.ensure_initialized()
        if cursor < 0:
            raise ValueError("cursor must be >= 0")

        file_size = self.log_path.stat().st_size
        if cursor > file_size:
            raise ValueError(
                f"cursor {cursor} is beyond current log size {file_size}; "
                "the log may have been reset"
            )

        with self.log_path.open("rb") as stream:
            stream.seek(cursor)
            raw = stream.read()
            to_cursor = stream.tell()

        text = raw.decode("utf-8")
        lines = text.splitlines()
        return {
            "server_id": server_id,
            "from_cursor": cursor,
            "to_cursor": to_cursor,
            "lines": lines,
        }

    def get_server_health(self, server_id: str) -> dict[str, object]:
        self._validate_server_id(server_id)
        return {"server_id": server_id, **self._read_state()["health"]}

    def get_thread_pool_status(self, server_id: str) -> dict[str, object]:
        self._validate_server_id(server_id)
        return {"server_id": server_id, **self._read_state()["thread_pool"]}

    def get_datasource_status(self, server_id: str) -> dict[str, object]:
        self._validate_server_id(server_id)
        return {"server_id": server_id, **self._read_state()["datasource"]}

    def get_deployment_status(self, server_id: str) -> dict[str, object]:
        self._validate_server_id(server_id)
        return {"server_id": server_id, **self._read_state()["deployment"]}

    def get_recent_config_changes(self, server_id: str) -> dict[str, object]:
        self._validate_server_id(server_id)
        return {
            "server_id": server_id,
            "changes": list(self._read_state()["recent_config_changes"]),
        }

    def ensure_initialized_without_logs_if_needed(self) -> None:
        """Initialize state + empty log without recursively appending boot logs."""

        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            state = json.loads(json.dumps(_DEFAULT_STATE))
            state["server_id"] = self.server_id
            self._write_state(state)
        if not self.log_path.exists():
            self.log_path.write_text("", encoding="utf-8")

    def _validate_server_id(self, server_id: str) -> None:
        if server_id != self.server_id:
            raise ValueError(f"unknown server_id: {server_id}")

    def _read_state(self) -> dict[str, Any]:
        self.ensure_initialized_without_logs_if_needed()
        with self.state_path.open("r", encoding="utf-8") as stream:
            return json.load(stream)

    def _write_state(self, state: dict[str, Any]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("w", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2)
