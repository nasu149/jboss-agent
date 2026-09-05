from langchain_core.messages import AIMessage

from jboss_agent.config import Settings
from jboss_agent.llm.gemini import build_gemini_client, ping_gemini


class FakeGeminiClient:
    def invoke(self, input: str) -> AIMessage:  # noqa: A002
        assert input == "Reply with exactly: GEMINI_CONNECTION_OK"
        return AIMessage(content="GEMINI_CONNECTION_OK")


def test_ping_gemini_without_network() -> None:
    settings = Settings(GOOGLE_API_KEY="test-key", GEMINI_MODEL="gemini-test-model")

    result = ping_gemini(settings, client=FakeGeminiClient())

    assert result.model == "gemini-test-model"
    assert result.response_text == "GEMINI_CONNECTION_OK"


def test_build_gemini_client_requires_api_key() -> None:
    settings = Settings(GOOGLE_API_KEY="")

    try:
        build_gemini_client(settings)
    except RuntimeError as exc:
        assert "GOOGLE_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError when GOOGLE_API_KEY is missing")
