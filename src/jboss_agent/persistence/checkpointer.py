"""Checkpointer factories.

STEP 7 supports memory or SQLite for comparison. STEP 10-12 intentionally use
``open_durable_checkpointer`` so a fixed monitoring thread and pending approval
survive scheduler/UI process restarts.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from langgraph.checkpoint.memory import InMemorySaver

from jboss_agent.config import Settings


@asynccontextmanager
async def open_checkpointer(settings: Settings) -> AsyncIterator[Any]:
    if settings.checkpoint_backend == "memory":
        yield InMemorySaver()
        return

    if settings.checkpoint_backend == "sqlite":
        async with _open_sqlite(settings.checkpoint_db_path) as saver:
            yield saver
        return

    raise ValueError(f"unsupported CHECKPOINT_BACKEND: {settings.checkpoint_backend}")


@asynccontextmanager
async def open_durable_checkpointer(settings: Settings) -> AsyncIterator[Any]:
    """Open the SQLite checkpointer required by the operational STEP 10-12 path."""
    async with _open_sqlite(settings.checkpoint_db_path) as saver:
        yield saver


@asynccontextmanager
async def _open_sqlite(path: str) -> AsyncIterator[Any]:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
        await saver.setup()
        yield saver
