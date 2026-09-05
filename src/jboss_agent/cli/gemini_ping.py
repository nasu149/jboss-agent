"""CLI command for the STEP 0 Gemini connection check."""

from __future__ import annotations

import logging

from jboss_agent.config import get_settings
from jboss_agent.llm.gemini import ping_gemini


logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    logger.info("Checking Gemini connectivity with model=%s", settings.gemini_model)
    result = ping_gemini(settings)
    print(f"model={result.model}")
    print(f"response={result.response_text}")


if __name__ == "__main__":
    main()
