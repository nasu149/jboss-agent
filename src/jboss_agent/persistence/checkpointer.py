"""Checkpointer factory introduced in STEP 7.

Memory is convenient for learning. SQLite demonstrates that a pending interrupt
can survive a Python process restart as long as the same thread_id is reused.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Any

from langgraph.checkpoint.memory import InMemorySaver

from jboss_agent.config import Settings


@asynccontextmanager
async def open_checkpointer(settings: Settings) -> AsyncIterator[Any]:
    if settings.checkpoint_backend == "memory":
        yield InMemorySaver()
        return

    if settings.checkpoint_backend == "sqlite":
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        db_path = Path(settings.checkpoint_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
            await saver.setup()
            yield saver
        return

    raise ValueError(f"unsupported CHECKPOINT_BACKEND: {settings.checkpoint_backend}")
