from pathlib import Path

import pytest

from jboss_agent.config import Settings


@pytest.fixture
def clear_relevant_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "GOOGLE_API_KEY",
        "GEMINI_MODEL",
        "TEAMS_DRY_RUN",
        "TEAMS_WEBHOOK_URL",
        "POLL_INTERVAL_SECONDS",
        "SERVER_ID",
    ):
        monkeypatch.delenv(name, raising=False)


def test_settings_load_from_env_file(
    tmp_path: Path,
    clear_relevant_environment: None,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "GOOGLE_API_KEY=test-key",
                "GEMINI_MODEL=gemini-test-model",
                "TEAMS_DRY_RUN=false",
                "POLL_INTERVAL_SECONDS=30",
                "SERVER_ID=jboss-test",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.has_google_api_key is True
    assert settings.gemini_model == "gemini-test-model"
    assert settings.teams_dry_run is False
    assert settings.poll_interval_seconds == 30
    assert settings.server_id == "jboss-test"


def test_empty_secrets_are_treated_as_unconfigured(
    tmp_path: Path,
    clear_relevant_environment: None,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("GOOGLE_API_KEY=\nTEAMS_WEBHOOK_URL=\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.google_api_key is None
    assert settings.teams_webhook_url is None
    assert settings.has_google_api_key is False
