"""STEP 1/2 deterministic log collection node."""

from __future__ import annotations

from jboss_agent.graph.fake_logs import DEFAULT_FAKE_LOG_LINES
from jboss_agent.graph.state import CoreLearningState


def collect_fake_log(state: CoreLearningState) -> dict[str, object]:
    """Put fake JBoss log text into State without using an LLM.

    Later STEP 3 replaces the simple input source with cursor-based log reading.
    The rest of the graph can keep consuming ``log_text``.
    """

    lines = state.get("input_log_lines") or DEFAULT_FAKE_LOG_LINES
    trace = [*state.get("node_trace", []), "collect_fake_log"]
    return {
        "log_text": "\n".join(lines),
        "node_trace": trace,
    }
