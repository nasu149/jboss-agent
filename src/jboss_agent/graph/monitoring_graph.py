"""STEP 2: Gemini structured classification + Conditional Edge routing."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from jboss_agent.config import Settings, get_settings
from jboss_agent.graph.nodes.analyze_logs import make_analyze_logs_node
from jboss_agent.graph.nodes.classification_branches import (
    datasource_pool_branch,
    deployment_branch,
    normal_branch,
    thread_pool_branch,
    unknown_branch,
)
from jboss_agent.graph.nodes.collect_fake_log import collect_fake_log
from jboss_agent.graph.routes.monitoring_routes import route_by_category
from jboss_agent.graph.state import MonitoringState
from jboss_agent.llm.log_classifier import LogClassifier, build_log_classifier


def build_step2_graph(
    *,
    settings: Settings | None = None,
    classifier: LogClassifier | None = None,
):
    """Build and compile the STEP 2 graph.

    ``classifier`` is injectable so tests can verify graph routing without API
    calls. The real CLI omits it and therefore uses Gemini.
    """

    resolved_classifier = classifier or build_log_classifier(settings or get_settings())

    builder = StateGraph(MonitoringState)
    builder.add_node("collect_fake_log", collect_fake_log)
    builder.add_node("analyze_logs", make_analyze_logs_node(resolved_classifier))
    builder.add_node("normal_branch", normal_branch)
    builder.add_node("thread_pool_branch", thread_pool_branch)
    builder.add_node("datasource_pool_branch", datasource_pool_branch)
    builder.add_node("deployment_branch", deployment_branch)
    builder.add_node("unknown_branch", unknown_branch)

    builder.add_edge(START, "collect_fake_log")
    builder.add_edge("collect_fake_log", "analyze_logs")
    builder.add_conditional_edges("analyze_logs", route_by_category)

    for branch in (
        "normal_branch",
        "thread_pool_branch",
        "datasource_pool_branch",
        "deployment_branch",
        "unknown_branch",
    ):
        builder.add_edge(branch, END)

    return builder.compile()
