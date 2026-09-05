"""STEP 1 deterministic check node."""

from __future__ import annotations

from jboss_agent.graph.state import CoreLearningState

_ATTENTION_KEYWORDS = (" WARN ", " ERROR ", " FATAL ")


def simple_check(state: CoreLearningState) -> dict[str, object]:
    """Perform a deliberately simple Python-only keyword check.

    This node is intentionally naive. STEP 2 demonstrates why ambiguous log
    interpretation is a better fit for an LLM than a growing collection of
    ``if`` statements.
    """

    log_text = state.get("log_text", "")
    attention_found = any(keyword in log_text for keyword in _ATTENTION_KEYWORDS)
    result = "ATTENTION_KEYWORD_FOUND" if attention_found else "NO_ATTENTION_KEYWORD"
    trace = [*state.get("node_trace", []), "simple_check"]
    return {
        "simple_check_result": result,
        "node_trace": trace,
    }
