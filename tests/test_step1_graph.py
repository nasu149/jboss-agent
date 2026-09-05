from jboss_agent.graph.core_graph import build_step1_graph


def test_step1_graph_runs_nodes_in_order() -> None:
    graph = build_step1_graph()

    result = graph.invoke(
        {
            "input_log_lines": [
                "2026-09-05 18:00:00 INFO  [test] request accepted",
                "2026-09-05 18:00:01 ERROR [test] simulated failure",
            ]
        }
    )

    assert "simulated failure" in result["log_text"]
    assert result["simple_check_result"] == "ATTENTION_KEYWORD_FOUND"
    assert result["node_trace"] == ["collect_fake_log", "simple_check"]
