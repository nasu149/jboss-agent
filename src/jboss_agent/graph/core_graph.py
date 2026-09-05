"""STEP 1: smallest explicit LangGraph Graph API example in this project."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from jboss_agent.graph.nodes.collect_fake_log import collect_fake_log
from jboss_agent.graph.nodes.simple_check import simple_check
from jboss_agent.graph.state import CoreLearningState


def build_step1_graph():
    """Build and compile ``START -> collect_fake_log -> simple_check -> END``."""

    builder = StateGraph(CoreLearningState)
    builder.add_node("collect_fake_log", collect_fake_log)
    builder.add_node("simple_check", simple_check)

    builder.add_edge(START, "collect_fake_log")
    builder.add_edge("collect_fake_log", "simple_check")
    builder.add_edge("simple_check", END)

    return builder.compile()
