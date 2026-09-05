"""STEP 3 deterministic cursor-based log collection node."""

from __future__ import annotations

from typing import Protocol

from jboss_agent.graph.state import CursorMonitoringState


class LogDeltaReader(Protocol):
    """Small port used by the graph so STEP 3 is independent of storage details."""

    def read_server_log(self, server_id: str, cursor: int) -> dict[str, object]:
        ...


def make_collect_logs_node(reader: LogDeltaReader):
    """Create a node that reads exactly the bytes after ``previous_log_cursor``."""

    def collect_logs(state: CursorMonitoringState) -> dict[str, object]:
        server_id = state["server_id"]
        previous_cursor = state.get("previous_log_cursor", 0)
        result = reader.read_server_log(server_id, previous_cursor)

        lines = [str(line) for line in result.get("lines", [])]
        current_cursor = int(result["to_cursor"])
        trace = [*state.get("node_trace", []), "collect_logs"]
        return {
            "previous_log_cursor": previous_cursor,
            "current_log_cursor": current_cursor,
            "new_log_lines": lines,
            "log_text": "\n".join(lines),
            "has_new_logs": bool(lines),
            "node_trace": trace,
        }

    return collect_logs
