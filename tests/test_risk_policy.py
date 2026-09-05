from jboss_agent.domain.risk_policy import evaluate_action


def test_thread_pool_change_is_medium_and_validated() -> None:
    result = evaluate_action(
        {"type": "SET_THREAD_POOL_MAX_THREADS", "current_value": 20, "proposed_value": 80}
    )
    assert result.allowed is True
    assert result.risk == "MEDIUM"
    assert result.normalized_action["proposed_value"] == 80


def test_out_of_range_thread_pool_change_is_blocked() -> None:
    result = evaluate_action(
        {"type": "SET_THREAD_POOL_MAX_THREADS", "current_value": 20, "proposed_value": 999}
    )
    assert result.allowed is False
    assert result.risk == "BLOCKED"


def test_unknown_action_is_blocked() -> None:
    result = evaluate_action({"type": "EXECUTE_SHELL", "proposed_value": 80})
    assert result.allowed is False
    assert result.risk == "BLOCKED"
