from __future__ import annotations

from jboss_agent.graph.nodes.verify import make_recovery_route


def test_step9_recovery_route_loops_then_fail_safe() -> None:
    route = make_recovery_route(2)
    assert route({"recovered": False, "recovery_attempts": 1}) == "prepare_retry"
    assert route({"recovered": False, "recovery_attempts": 2}) == "fail_safe"
    assert route({"recovered": True, "recovery_attempts": 1}) == "recovered"
