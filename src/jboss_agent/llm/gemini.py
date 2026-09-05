"""Gemini client construction and STEP 0 connectivity check."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from jboss_agent.config import Settings


class InvokableChatModel(Protocol):
    """Small protocol that keeps the connectivity function easy to unit test."""

    def invoke(self, input: str) -> BaseMessage:  # noqa: A002 - LangChain API naming
        ...


@dataclass(frozen=True)
class GeminiPingResult:
    """Result returned by the STEP 0 Gemini connectivity check."""

    model: str
    response_text: str


def build_gemini_client(settings: Settings) -> ChatGoogleGenerativeAI:
    """Build a Gemini Developer API client from validated application settings.

    Raises:
        RuntimeError: If ``GOOGLE_API_KEY`` is not configured.
    """

    if not settings.has_google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not configured. Copy .env.example to .env and set your key."
        )

    assert settings.google_api_key is not None  # narrowed by has_google_api_key
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        api_key=settings.google_api_key.get_secret_value(),
        temperature=settings.gemini_temperature,
        timeout=30,
        max_retries=2,
    )


def ping_gemini(
    settings: Settings,
    *,
    client: InvokableChatModel | None = None,
) -> GeminiPingResult:
    """Send one deterministic connectivity prompt to Gemini.

    The function intentionally does not contain LangGraph logic. STEP 0 only
    verifies the external LLM dependency before graph construction begins.
    """

    model = client or build_gemini_client(settings)
    response = model.invoke(
        "Reply with exactly: GEMINI_CONNECTION_OK"
    )

    # Gemini 3 responses can expose content blocks, while LangChain's ``text``
    # property normalizes them to a string.
    response_text = response.text.strip()
    return GeminiPingResult(model=settings.gemini_model, response_text=response_text)
