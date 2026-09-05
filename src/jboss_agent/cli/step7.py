"""CLI runner for STEP 7 interrupt/checkpointer/thread_id."""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid

from langgraph.types import Command

from jboss_agent.config import get_settings
from jboss_agent.graph.approval_graph import build_step7_graph
from jboss_agent.persistence.checkpointer import open_checkpointer


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread-id", default=None)
    parser.add_argument("--pause-only", action="store_true")
    parser.add_argument("--resume-only", action="store_true")
    parser.add_argument("--decision", choices=["approve", "reject", "edit_and_approve"], default="approve")
    parser.add_argument("--value", type=int, default=80)
    return parser.parse_args()


def _resume_payload(args: argparse.Namespace) -> dict[str, object]:
    payload: dict[str, object] = {"decision": args.decision}
    if args.decision == "edit_and_approve":
        payload["proposed_value"] = args.value
    return payload


async def _run() -> None:
    args = _args()
    settings = get_settings()
    thread_id = args.thread_id or f"incident:{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    async with open_checkpointer(settings) as checkpointer:
        graph = build_step7_graph(checkpointer=checkpointer)

        if args.resume_only:
            result = await graph.ainvoke(Command(resume=_resume_payload(args)), config=config)
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
            return

        initial = {
            "incident_id": thread_id.split(":", 1)[-1],
            "server_id": settings.server_id,
            "diagnosis": {"reason": "max_threads appears to have regressed from 80 to 20"},
            "proposed_action": {
                "type": "SET_THREAD_POOL_MAX_THREADS",
                "current_value": 20,
                "proposed_value": 80,
                "deployment_name": None,
                "rationale": "restore the recently observed previous capacity",
            },
            "messages": [],
            "node_trace": [],
        }
        paused = await graph.ainvoke(initial, config=config)
        interrupts = paused.get("__interrupt__", ())
        print(f"thread_id={thread_id}")
        print(f"CHECKPOINT_BACKEND={settings.checkpoint_backend}")
        if interrupts:
            print("PAUSED by interrupt():")
            print(json.dumps(interrupts[0].value, ensure_ascii=False, indent=2, default=str))
        if args.pause_only:
            print("Stopped while pending. Re-run with --resume-only and the SAME --thread-id.")
            return

        result = await graph.ainvoke(Command(resume=_resume_payload(args)), config=config)
        print("RESUMED with Command(resume=...) using the same thread_id")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
