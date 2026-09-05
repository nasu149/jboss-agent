"""STEP 3: cursor-based incremental monitoring + STEP 2 LLM classification."""

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
from jboss_agent.graph.nodes.collect_logs import LogDeltaReader, make_collect_logs_node
from jboss_agent.graph.nodes.no_new_logs import no_new_logs
from jboss_agent.graph.routes.cursor_routes import route_on_new_logs
from jboss_agent.graph.routes.monitoring_routes import route_by_category
from jboss_agent.graph.state import CursorMonitoringState
from jboss_agent.jboss.fake_operations import FakeJBossOperations
from jboss_agent.llm.log_classifier import LogClassifier, build_log_classifier


def build_step3_graph(
    *,
    settings: Settings | None = None,
    reader: LogDeltaReader | None = None,
    classifier: LogClassifier | None = None,
):
    """Compile the STEP 3 graph.

    The reader is ordinary deterministic Python. Gemini is reached only after
    ``route_on_new_logs`` confirms there is a non-empty delta.
    """

    resolved_settings = settings or get_settings()
    resolved_reader = reader or FakeJBossOperations(
        resolved_settings.fake_jboss_data_dir,
        server_id=resolved_settings.server_id,
    )
    resolved_classifier = classifier or build_log_classifier(resolved_settings)

    builder = StateGraph(CursorMonitoringState)
    builder.add_node("collect_logs", make_collect_logs_node(resolved_reader))
    builder.add_node("no_new_logs", no_new_logs)
    builder.add_node("analyze_logs", make_analyze_logs_node(resolved_classifier))
    builder.add_node("normal_branch", normal_branch)
    builder.add_node("thread_pool_branch", thread_pool_branch)
    builder.add_node("datasource_pool_branch", datasource_pool_branch)
    builder.add_node("deployment_branch", deployment_branch)
    builder.add_node("unknown_branch", unknown_branch)

    builder.add_edge(START, "collect_logs")
    builder.add_conditional_edges("collect_logs", route_on_new_logs)
    builder.add_edge("no_new_logs", END)
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
