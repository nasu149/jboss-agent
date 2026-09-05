"""Simulator-only ground-truth persistence.

No graph/node imports this module. The UI and evaluation harness may read it
*after* agent execution for comparison.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from jboss_agent.runtime.store import utc_now_iso
from jboss_agent.simulator.scenarios import GroundTruthScenario


@dataclass(frozen=True)
class GroundTruthEvent:
    event_id: str
    server_id: str
    scenario: GroundTruthScenario
    injected_at: str
    linked_incident_id: str | None


class GroundTruthStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ground_truth_events (
                    event_id TEXT PRIMARY KEY,
                    server_id TEXT NOT NULL,
                    scenario TEXT NOT NULL,
                    injected_at TEXT NOT NULL,
                    linked_incident_id TEXT
                )
                """
            )

    def record(self, event_id: str, server_id: str, scenario: GroundTruthScenario) -> GroundTruthEvent:
        injected_at = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ground_truth_events(event_id, server_id, scenario, injected_at)
                VALUES (?, ?, ?, ?)
                """,
                (event_id, server_id, scenario, injected_at),
            )
        return GroundTruthEvent(event_id, server_id, scenario, injected_at, None)

    def link_latest_unlinked(self, server_id: str, incident_id: str) -> str | None:
        """Link an incident without returning the hidden scenario to agent runtime code."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT event_id FROM ground_truth_events
                WHERE server_id=? AND linked_incident_id IS NULL
                ORDER BY injected_at DESC LIMIT 1
                """,
                (server_id,),
            ).fetchone()
            if row is None:
                return None
            event_id = str(row["event_id"])
            conn.execute(
                "UPDATE ground_truth_events SET linked_incident_id=? WHERE event_id=?",
                (incident_id, event_id),
            )
            return event_id

    def get(self, event_id: str) -> GroundTruthEvent | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM ground_truth_events WHERE event_id=?", (event_id,)
            ).fetchone()
        return _row_to_event(row) if row else None

    def get_by_incident(self, incident_id: str) -> GroundTruthEvent | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM ground_truth_events WHERE linked_incident_id=?", (incident_id,)
            ).fetchone()
        return _row_to_event(row) if row else None

    def latest(self, server_id: str) -> GroundTruthEvent | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM ground_truth_events WHERE server_id=?
                ORDER BY injected_at DESC LIMIT 1
                """,
                (server_id,),
            ).fetchone()
        return _row_to_event(row) if row else None

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM ground_truth_events")


def _row_to_event(row: sqlite3.Row) -> GroundTruthEvent:
    return GroundTruthEvent(
        event_id=row["event_id"],
        server_id=row["server_id"],
        scenario=row["scenario"],
        injected_at=row["injected_at"],
        linked_incident_id=row["linked_incident_id"],
    )
