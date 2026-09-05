"""Helpers for normalizing LangChain MCP Tool return values."""

from __future__ import annotations

import json
from typing import Any


def normalize_tool_result(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"raw": value}
    if hasattr(value, "content"):
        return normalize_tool_result(value.content)
    return {"raw": value}
